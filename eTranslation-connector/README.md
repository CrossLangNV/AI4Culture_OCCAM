# CEF eTranslation connector

## Set-up

Set environment variables

 - ETRANSLATION_USERNAME=<as provided by CEF eTranslation>
 - ETRANSLATION_PASSWORD=<as provided by CEF eTranslation>
 - CALLBACK_URL=<exposed url of etranslation-connector>
 - SNIPPET_CALLBACK_URL=<exposed url of etranslation-connector>/hook/snippet (optional, overrides CALLBACK_URL)
 - DOCUMENT_CALLBACK_URL=<exposed url of etranslation-connector>/hook/document (optional, overrides CALLBACK_URL)

To run production server:
```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d --build
```

### Publish

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml push
```

## Callback 

For callback, you have to expose the server to the internet. 

You can use tools like localhost.run or ngrok. We will use Ngrok

```bash
ngrok http 28000 &
```

Copy the forwarding url and set it as CALLBACK_URL

