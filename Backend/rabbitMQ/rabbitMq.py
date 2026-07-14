import aio_pika
from dotenv import load_dotenv
load_dotenv()
import os

RABBIT_URL = os.getenv("AMQP_URL")

connection = None
channel = None

async def connect():
    global connection, channel

    if channel is not None:
        return channel

    if not RABBIT_URL:
        raise RuntimeError("AMQP_URL is not configured")

    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    print("RabbitMQ Connected")

    return channel


async def get_channel():
    if channel is None:
        return await connect()
    return channel