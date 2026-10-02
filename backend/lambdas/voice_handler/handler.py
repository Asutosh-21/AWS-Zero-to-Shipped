import json
import boto3
import os
import base64

transcribe = boto3.client("transcribe", region_name="us-east-1")
polly = boto3.client("polly", region_name="us-east-1")
translate = boto3.client("translate", region_name="us-east-1")
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
s3 = boto3.client("s3", region_name="us-east-1")

S3_BUCKET_UPLOADS = os.environ["S3_BUCKET_UPLOADS"]
SUPERVISOR_AGENT_ID = os.environ["BEDROCK_AGENT_SUPERVISOR_ID"]
SUPERVISOR_AGENT_ALIAS = os.environ.get("BEDROCK_AGENT_SUPERVISOR_ALIAS", "LIVE")

LANGUAGE_VOICE_MAP = {
    "en": {"transcribe": "en-US", "polly": "Joanna", "polly_engine": "neural"},
    "es": {"transcribe": "es-US", "polly": "Lupe", "polly_engine": "neural"},
    "fr": {"transcribe": "fr-FR", "polly": "Lea", "polly_engine": "neural"},
    "zh": {"transcribe": "zh-CN", "polly": "Zhiyu", "polly_engine": "neural"},
    "pt": {"transcribe": "pt-BR", "polly": "Camila", "polly_engine": "neural"},
}


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    audio_base64 = body.get("audio")
    language_code = body.get("language", "en")
    session_id = body.get("sessionId", context.aws_request_id)
    user_id = event.get("requestContext", {}).get("authorizer", {}).get("sub", "anonymous")

    if not audio_base64:
        return {"statusCode": 400, "body": json.dumps({"error": "audio is required"})}

    audio_bytes = base64.b64decode(audio_base64)
    s3_key = f"user-uploads/{user_id}/voice-{context.aws_request_id}.mp3"
    s3.put_object(Bucket=S3_BUCKET_UPLOADS, Key=s3_key, Body=audio_bytes, ContentType="audio/mpeg")

    lang_config = LANGUAGE_VOICE_MAP.get(language_code, LANGUAGE_VOICE_MAP["en"])
    transcribed_text = _transcribe_audio(s3_key, lang_config["transcribe"])

    if not transcribed_text:
        return {"statusCode": 422, "body": json.dumps({"error": "Could not transcribe audio"})}

    query_in_english = transcribed_text
    if language_code != "en":
        translate_response = translate.translate_text(
            Text=transcribed_text,
            SourceLanguageCode=language_code,
            TargetLanguageCode="en",
        )
        query_in_english = translate_response["TranslatedText"]

    bedrock_response = bedrock_agent_runtime.invoke_agent(
        agentId=SUPERVISOR_AGENT_ID,
        agentAliasId=SUPERVISOR_AGENT_ALIAS,
        sessionId=f"voice-{session_id}",
        inputText=query_in_english,
    )

    response_text_english = ""
    for event_stream in bedrock_response.get("completion", []):
        if "chunk" in event_stream:
            response_text_english += event_stream["chunk"].get("bytes", b"").decode("utf-8")

    response_text = response_text_english
    if language_code != "en":
        translate_back = translate.translate_text(
            Text=response_text_english[:4500],
            SourceLanguageCode="en",
            TargetLanguageCode=language_code,
        )
        response_text = translate_back["TranslatedText"]

    polly_response = polly.synthesize_speech(
        Text=response_text[:3000],
        OutputFormat="mp3",
        VoiceId=lang_config["polly"],
        Engine=lang_config["polly_engine"],
    )

    audio_response_base64 = base64.b64encode(
        polly_response["AudioStream"].read()
    ).decode("utf-8")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({
            "transcribedText": transcribed_text,
            "responseText": response_text,
            "audioResponse": audio_response_base64,
            "language": language_code,
            "sessionId": session_id,
        }),
    }


def _transcribe_audio(s3_key, language_code):
    import time
    job_name = f"nutriroute-{s3_key.replace('/', '-').replace('.', '-')}"
    s3_uri = f"s3://{S3_BUCKET_UPLOADS}/{s3_key}"

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="mp3",
        LanguageCode=language_code,
    )

    for _ in range(30):
        time.sleep(2)
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
        if job_status == "COMPLETED":
            transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
            import urllib.request
            with urllib.request.urlopen(transcript_uri) as response:
                transcript_data = json.loads(response.read())
            return transcript_data["results"]["transcripts"][0]["transcript"]
        if job_status == "FAILED":
            return None

    return None
