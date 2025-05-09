#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import argparse
import asyncio
import os
import random
import uuid
import uvicorn
import asyncio

from starlette.applications import Starlette
from starlette.responses import FileResponse, Response
from sse_starlette.sse import EventSourceResponse
from starlette.staticfiles import StaticFiles
import httpx

process_id = f"frontend-{uuid.uuid4().hex[:8]}"
records = list()

async def startup():
    """Starts the background task to fetch and forward events."""
    asyncio.create_task(forward_events())

star = Starlette(debug=True, on_startup=[startup])
star.mount("/static", StaticFiles(directory="static"), name="static")

@star.route("/")
async def index(request):
    return FileResponse("static/index.html")

# Keep track of connected clients (their response generators)
subscribers = set()

async def fetch_events():
    """Connects to Event Source and yields events with continuous reconnection."""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                print(f"Attempting to connect to Event Source A at {f"{backend_url}/api/notifications"}")
                async with client.stream("GET", f"{backend_url}/api/notifications", timeout=None) as response:
                    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            yield line[len("data:"):].strip()
                        elif line == "":
                            continue # Keep-alive or other empty lines
            except httpx.HTTPError as e:
                print(f"HTTP error from Event Source A: {e}")
            except httpx.ConnectError as e:
                print(f"Connection error to Event Source A: {e}")
            except Exception as e:
                print(f"An unexpected error occurred while fetching events: {e}")

            wait_time = 1
            print(f"Lost connection to Event Source A. Retrying in {wait_time:.2f} seconds...")
            await asyncio.sleep(wait_time)

async def forward_events():
    async for event in fetch_events():
        dead_clients = set()
        for queue in subscribers:
            try:
                await queue.put(f"data: {event}\n\n")
            except asyncio.QueueFull:
                print("Client queue full, might be slow or disconnected.")
                dead_clients.add(queue)
            except Exception as e:
                print(f"Error sending to client: {e}")
                dead_clients.add(queue)
        subscribers.difference_update(dead_clients)

@star.route("/api/notifications")
async def notifications(request):
    """SSE endpoint for clients to subscribe."""
    queue: asyncio.Queue = asyncio.Queue()
    subscribers.add(queue)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield event.encode()
        except asyncio.CancelledError:
            print("Client disconnected.")
        finally:
            subscribers.remove(queue)

    return EventSourceResponse(event_generator())

@star.route("/api/health", methods=["GET"])
async def health(request):

    return Response("OK\n", 200)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--backend", metavar="URL", default="http://flight-data-provider:8080")

    args = parser.parse_args()

    global backend_url
    backend_url = args.backend

    uvicorn.run(star, host=args.host, port=args.port)
