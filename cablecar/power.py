import asyncio
import enum
import typing
import logging

import asyncua.sync

import cablecar
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
        self._logger: logging.Logger = logging.getLogger(
            f"CableCarSim.{self.__class__.__name__}.{name}"
        )
        self._name = name
        self._objects: typing.Dict[str, asyncua.sync.SyncNode] = {}
        self._max_speed = speed
        self._server: cab_server.SimulationServer = server
        self._direction = cab_com.Direction.FORWARD
        self._namespace: int = self._server.register_namespace(
            f"{self.__class__.__name__}.{self._name}"
        )
        self._create_objects()
        self._server.add_task(self.listener)
        self._server.add_task(self.speed_setter)

    @property
    def speed(self) -> float:
        return self._objects["SPEED"].get_value()

    @speed.setter
    @cablecar.ignore_no_change
    def speed(self, value: float) -> None:
        self._logger.info(f"SPEED={value}")
        self._objects["SPEED"].set_value(value)

    @property
    def server(self) -> cab_server.SimulationServer:
        return self._server

    def _create_objects(self) -> None:
        self._objects["STATUS"] = self._server.add_variable(
            self._namespace, f"{self._name.upper()}_STATUS", f"{self._name} Winder Status", cablecar.enum_member_str(Status.STOPPED)
        )

        self._objects["CONTROLLER"] = self._server.add_variable(
            self._namespace, f"{self._name.upper()}_CONTROLLER", f"{self._name} Winder Controller", cablecar.enum_member_str(Controller.NONE)
        )

        self._objects["SPEED"] = self._server.add_variable(
            self._namespace, f"{self._name.upper()}_SPEED", f"{self._name} Winder Speed", 0.0
        )

        self._objects["CONTROLLER"].set_writable()

    @property
    def status(self) -> Status:
        return getattr(Status, self._objects["STATUS"].get_value())

    @property
    def controller(self) -> Controller:
        return getattr(Controller, self._objects["CONTROLLER"].get_value())

    @controller.setter
    @cablecar.ignore_no_change
    def controller(self,  value: Controller) -> None:
        self._logger.info(f"CONTROLLER={value}")
        self._objects["CONTROLLER"].set_value(cablecar.enum_member_str(value))

    @status.setter
    @cablecar.ignore_no_change
    def status(self, value: Status) -> None:
        self._logger.info(f"STATUS={value}")
        self._objects["STATUS"].set_value(cablecar.enum_member_str(value))

    async def stop(self) -> None:
        self.status = Status.STOPPED

    async def speed_setter(self) -> None:
        while self._server.running:
            await asyncio.sleep(0.5)
            if self.status == Status.CLOCKWISE:
                self.speed = self._max_speed
            elif self.status == Status.COUNTER_CLOCKWISE:
                self.speed = -self._max_speed
            else:
                self.speed = 0.0

    async def listener(self) -> None:
        while self._server.running:
            await asyncio.sleep(0.5)
            if self.controller == Controller.NONE:
                continue
            elif self.controller == Controller.OFF:
                self.status = Status.STOPPED
            elif self.controller == Controller.SWITCH_DIRECTION:
                if self.status != Status.STOPPED:
                    continue
                if self._direction == cab_com.Direction.FORWARD:
                    self._direction = cab_com.Direction.REVERSE
                    self.status = Status.COUNTER_CLOCKWISE
                else:
                    self._direction = cab_com.Direction.FORWARD
                    self.status = Status.CLOCKWISE
            elif self.controller == Controller.ON:
                if self.status != Status.STOPPED:
                    continue
                if self._direction == cab_com.Direction.FORWARD:
                    self.status = Status.CLOCKWISE
                else:
                    self.status = Status.COUNTER_CLOCKWISE
            self.controller = Controller.NONE
