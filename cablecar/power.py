import asyncio
import enum
import typing

import asyncua.sync

import cablecar.common as cab_com
import cablecar.server as cab_server


class Status(enum.Enum):
    STOPPED = enum.auto()
    COUNTER_CLOCKWISE = enum.auto()
    CLOCKWISE = enum.auto()


class Controller(enum.Enum):
    OFF = enum.auto()
    ON = enum.auto()
    SWITCH_DIRECTION = enum.auto()
    NONE = enum.auto()


class Winder:
    def __init__(
        self, name: str, server: cab_server.SimulationServer, speed: float = 4.25
    ) -> None:
        self._name = name
        self._objects: typing.Dict[str, asyncua.sync.SyncNode] = {}
        self._max_speed = speed
        self._current_speed = 0.0
        self._server: cab_server.SimulationServer = server
        self._direction = cab_com.Direction.FORWARD
        self._namespace: int = self._server.register_namespace(
            f"{self.__class__.__name__}.{self._name}"
        )
        self._create_objects()
        self._server.add_task(self.listener)

    @property
    def speed(self) -> float:
        return self._current_speed

    @property
    def server(self) -> cab_server.SimulationServer:
        return self._server

    def _create_objects(self) -> None:
        self._objects["STATUS"] = self._server.add_variable(
            self._namespace, "STATUS", "Winder Status", Status.STOPPED.value
        )

        self._objects["CONTROLLER"] = self._server.add_variable(
            self._namespace, "CONTROLLER", "Winder Controller", Controller.NONE.value
        )

        self._objects["CONTROLLER"].set_writable()

    @property
    def status(self) -> Status:
        return Status(self._objects["STATUS"].get_value())

    @status.setter
    def status(self, value: Status) -> None:
        self._objects["STATUS"].set_value(value.value)

    async def stop(self) -> None:
        self.status = Status.STOPPED

    async def listener(self) -> None:
        while self._server.running:
            _controller_val: int = self._objects["CONTROLLER"].get_value()
            if _controller_val == Controller.NONE.value:
                continue
            elif _controller_val == Controller.OFF.value:
                self.status = Status.STOPPED
                self._current_speed = 0.0
            elif _controller_val == Controller.SWITCH_DIRECTION.value:
                if self.status != Status.STOPPED:
                    continue
                if self._direction == cab_com.Direction.FORWARD:
                    self._direction = cab_com.Direction.REVERSE
                    self.status = Status.COUNTER_CLOCKWISE
                    self._current_speed = -self._max_speed
                else:
                    self._direction = cab_com.Direction.FORWARD
                    self.status = Status.CLOCKWISE
                    self._current_speed = self._max_speed
            elif _controller_val == Controller.ON.value:
                if self.status != Status.STOPPED:
                    continue
                if self._direction == cab_com.Direction.FORWARD:
                    self.status = Status.CLOCKWISE
                else:
                    self.status = Status.COUNTER_CLOCKWISE
            self._objects["CONTROLLER"].set_value(Controller.NONE.value)
            await asyncio.sleep(1)
