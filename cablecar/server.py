import asyncio
import logging
import typing

import asyncua.sync
import asyncua.ua


class SimulationServer(asyncua.sync.Server):
    def __init__(self, port: int = 4080) -> None:
        super().__init__()
        self._logger: logging.Logger = logging.getLogger(
            f"CableCarSim.{self.__class__.__name__}"
        )
        self._run_sim: bool = True
        self._async_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self._async_tasks: typing.List[typing.Coroutine] = []
        self._url: str = f"opc.tcp://127.0.0.1:{port}/freeopcua/server"
        self.set_endpoint(self._url)

    @property
    def running(self) -> bool:
        return self._run_sim

    @property
    def objects_node(self) -> asyncua.sync.SyncNode:
        return self.get_node(
            asyncua.ua.TwoByteNodeId(asyncua.ua.ObjectIds.ObjectsFolder)
        )

    def add_task(self, task: typing.Coroutine) -> None:
        self._async_tasks.append(task)

    async def launch(self) -> None:
        try:
            await asyncio.wait(
                [i() for i in self._async_tasks], return_when=asyncio.FIRST_COMPLETED
            )
        except KeyboardInterrupt:
            return

    def add_variable(
        self, namespace: int, label: str, description: str, start_val: typing.Any
    ) -> asyncua.sync.SyncNode:
        return self.objects_node.add_variable(
            f"ns={namespace};s={label}", description, start_val
        )

    def __enter__(self) -> "SimulationServer":
        self._logger.info(f"Starting server on: {self._url}")
        self.start()
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self._run_sim = False
        self._logger.info("Stopping server")
        self.stop()
