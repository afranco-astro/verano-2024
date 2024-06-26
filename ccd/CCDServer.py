import asyncio
import random
import uuid

TCP_HOST = "127.0.0.1"
TCP_PORT = 8888

class CCDServer:
    def __init__(self):
        self.status = "IDLE"
        self.binning = (1, 1)
        self.current_exposure_id = None
        self.exposure_time = None
        self.exposure_task = None
        self.progress = 0
        self.lock = asyncio.Lock()

    async def init(self, binning):
        async with self.lock:
            self.binning = binning
            self.status = "LISTO"
        return "CCD Listo"

    async def start_exposure(self, time):
        async with self.lock:
            if self.status == "EXPONIENDO":
                return "Error: El CCD se encuentra exponiendo"
            self.status = "EXPONIENDO"
            self.exposure_time = time
            self.progress = 0
            self.current_exposure_id = str(uuid.uuid4())
            
            self.exposure_task = asyncio.create_task(self._simulate_exposure(time))

        return f"ID: {self.current_exposure_id.lower()}"

    async def get_progress(self, exposure_id):
        async with self.lock:
            if self.current_exposure_id == None or exposure_id == self.current_exposure_id:
                return f"{self.progress}"
        return "Error: Identificador Invalido"

    async def get_status(self):
        async with self.lock:
            return f"{self.status}"

    async def get_temp(self):
        async with self.lock:
            raw = random.uniform(-120, -105)
            return f"{round(raw, 2)}"

    async def _simulate_exposure(self, time):
        for i in range(100):
            await asyncio.sleep(0.3)
            async with self.lock:
                self.progress = i
                print(f"Progreso: {self.progress}")

        async with self.lock:
            self.progress = 100
            self.status = "LISTO"
            self.current_exposure_id = None
            self.exposure_task = None

async def handle_client(reader, writer, ccd_server):
    while True:
        data = await reader.read(100)
        if not data:
            break
        
        message = data.decode().strip().upper()
        response = "Comando Invalido"
        
        if message.startswith("INIT"):
            _, bin_x, bin_y = message.split()
            response = await ccd_server.init((int(bin_x), int(bin_y)))
        elif message.startswith("EXPONE"):
            _, time = message.split()
            response = await ccd_server.start_exposure(int(time))
        elif message.startswith("PROGRESO"):
            _, exposure_id = message.split()
            response = await ccd_server.get_progress(exposure_id.lower())
        elif message == "STATUS":
            response = await ccd_server.get_status()
        elif message == "TEMP":
            response = await ccd_server.get_temp()

        writer.write(response.encode('UTF-8') + b'\n')
        await writer.drain()

    writer.close()

async def main():
    ccd_server = CCDServer()
    server = await asyncio.start_server(lambda r, w: handle_client(r, w, ccd_server), TCP_HOST, TCP_PORT)
    print(f'Escuchando peticiones tcp socket: {TCP_HOST}:{TCP_PORT}')
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
