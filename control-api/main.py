import asyncio
import uvicorn
import paho.mqtt.client as mqtt
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from routes.api import router as api_router
from src.endpoints.send_to_device import MQTT_BROKER_HOST, MQTT_BROKER_PORT
from src.endpoints.mqtt_stream import on_message as stream_on_message, set_event_loop as set_stream_event_loop

app = FastAPI(docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
        redoc_favicon_url="/static/favicon.png",
    )

STREAM_TOPICS = [
    "device/+/command",
    "send_message/qr",
    "update_schedule",
    "mq_update_schedule",
    "staff_access/#",
    "camera/person-count",
    "toggle_popup/popup",
]

stream_client = mqtt.Client(client_id="control-api-mqtt-stream")
stream_client.on_message = stream_on_message


@app.on_event("startup")
def start_mqtt_stream_client():
    set_stream_event_loop(asyncio.get_event_loop())
    stream_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
    for topic in STREAM_TOPICS:
        stream_client.subscribe(topic, qos=1)
    stream_client.loop_start()


@app.on_event("shutdown")
def stop_mqtt_stream_client():
    stream_client.loop_stop()
    stream_client.disconnect()

origins = ["http://localhost:8000","http://0.0.0.0:80000"]

# CLIENT_ID = os.getenv('25133f28f9e842998a662eb4b935cf2a')
# TENANT_ID = os.getenv('8b060fcf-29fd-4b25-a613-c4712345cfd9')
# AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
# SCOPE = ['User.Read']

app.add_middleware(
     CORSMiddleware,
     allow_origins=["*"],
     allow_credentials=True,
     allow_methods=["*"],  # HTTP methods to allow
     allow_headers=["*"]
)

app.include_router(api_router)
if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=8000, log_level="info",reload=True)#Developer code
    # command: uvicorn app.main:app --host 0.0.0.0
    #**********Production********************************
    #uvicorn.run(app, host="0.0.0.0", port=8000)  make for production code
    #bash uvicorn main:app --reload
    # Security SSL isAuthen
    #uvicorn.run("main:app", host='0.0.0.0', port=5000, log_level="info", ssl_keyfile="/etc/apache2/ssl/apache.key", ssl_certfile="/etc/apache2/ssl/apache.crt",   reload=True)
#    print("running")
