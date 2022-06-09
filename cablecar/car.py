import asyncio
import enum
import logging
import typing

import asyncua.sync
import asyncua.ua

import cablecar.common as cab_com
import cablecar.route as cab_route
import cablecar.server as cab_server


class GripState(enum.Enum):
    ENGAGED = enum.auto()
    LOOSE = enum.auto()
    RELEASED = enum.auto()


class Controller(enum.Enum):
    GRIP_ENGAGE = enum.auto()
    GRIP_LOOSE = enum.auto()
    GRIP_RELEASE = enum.auto()
    RAIL_BRAKE_APPLY = enum.auto()
    RAIL_BRAKE_RELEASE = enum.auto()
    SHOE_BRAKE_APPLY = enum.auto()
    SHOE_BRAKE_RELEASE = enum.auto()
    BELL_RING = enum.auto()
    NONE = enum.auto()


class CableCar:
    def __init__(self, number: int) -> None:
        self._logger: logging.Logger = logging.getLogger(
            f"CableCarSim.{self.__class__.__name__}.Car_{number}"
        )
        self._number: int = number
        self._server: typing.Optional[cab_server.SimulationServer] = None
        self._forward_direction: cab_com.Direction = cab_com.Direction.FORWARD
        self._route: typing.Optional[cab_route.Route] = None
        self._namespace: typing.Optional[int] = None
        self._objects: typing.Dict[str, asyncua.sync.SyncNode] = {}
        self._acceleration: float = 0.1

    @property
    def objects_node(self) -> asyncua.sync.SyncNode:
        return self._server.get_node(
            asyncua.ua.TwoByteNodeId(asyncua.ua.ObjectIds.ObjectsFolder)
        )

    def _create_objects(self) -> None:
        if not self._server:
            raise AssertionError("Cannot create objects without route assignment")

        self._objects["CURRENT_LOCATION"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_LOCATION"',
            f"Cable Car {self._number} Location",
            "Depot",
        )

        self._objects["CURRENT_POSITION"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_POSITION"',
            f"Cable Car {self._number} Position",
            0.0,
        )

        self._objects["GRIP_STATE"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_GRIPSTATE"',
            f"Cable Car {self._number} Grip State",
            GripState.RELEASED.value,
        )

        self._objects["CURRENT_SPEED"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_SPEED"',
            f"Cable Car {self._number} Speed",
            0.0,
        )

        self._objects["CONTROLLER"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_CONTROLLER"',
            f"Cable Car {self._number} Controller",
            Controller.NONE.value,
        )
        self._objects["CONTROLLER"].set_writable()

        self._objects["BELL"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_BELL"',
            f"Cable Car {self._number} Bell",
            False,
        )

    @property
    def grip_state(self) -> GripState:
        return GripState(self._objects["GRIP_STATE"].get_value())

    @grip_state.setter
    def grip_state(self, state: GripState) -> None:
        self._logger.info(f"GRIP_STATE={state}")
        self._objects["GRIP_STATE"].set_value(state.value)

    @property
    def speed(self) -> float:
        return float(self._objects["CURRENT_SPEED"].get_value())

    @speed.setter
    def setter(self, speed: float) -> None:
        self._logger.info(f"CURRENT_SPEED={speed}")
        self._objects["CURRENT_SPEED"].set_value(speed)

    @property
    def controller(self) -> Controller:
        return Controller(self._objects["CONTROLLER"].get_value())

    @property
    def bell(self) -> bool:
        return self._objects["BELL"].get_value()

    async def ring_bell(self) -> None:
        self._objects["BELL"].set_value(True)
        await asyncio.sleep(1)
        self._objects["BELL"].set_value(False)

    def add_to_route(self, route: cab_route.Route, distance: float = 0.0) -> None:
        self._server = route.winder.server
        self._namespace = self._server.register_namespace(
            f"{self.__class__.__name__}.CableCar{self._number}"
        )
        self._create_objects()
        self._route = route
        self.position = distance

        self._server.add_task(self._check_bell_trigger)
        self._server.add_task(self._check_grip_trigger)
        self._server.add_task(self._drive)

    @property
    def position(self) -> float:
        return self._objects["CURRENT_POSITION"].get_value()

    @property
    def location(self) -> str:
        return self._objects["CURRENT_LOCATION"].get_value()

    @position.setter
    def position(self, distance: float) -> None:
        self._logger.info(f"CURRENT_POSITION={distance}")
        self._objects["CURRENT_POSITION"].set_value(distance)

    @location.setter
    def location(self, location: str) -> None:
        self._logger.info(f"CURRENT_LOCATION={location}")
        self._objects["CURRENT_LOCATION"].set_value(location)

    async def _check_bell_trigger(self) -> None:
        while self._server.running:
            await asyncio.sleep(0.5)
            if self.controller == Controller.BELL_RING:
                await self.ring_bell()

    async def _check_grip_trigger(self) -> None:
        while self._server.running:
            print("BUZZ")
            await asyncio.sleep(1)
            if self.controller == Controller.GRIP_ENGAGE:
                if self.grip_state == GripState.ENGAGED:
                    continue
                elif self.grip_state == GripState.LOOSE:
                    _duration = 1
                else:
                    _duration = 3
                for _ in range(_duration):
                    await asyncio.sleep(1)
                self.grip_state = GripState.ENGAGED
            elif self.controller == Controller.GRIP_LOOSE:
                if self.grip_state == GripState.LOOSE:
                    continue
                self.grip_state = GripState.LOOSE
            elif self.controller == Controller.GRIP_RELEASE:
                if self.grip_state == GripState.RELEASED:
                    continue
                elif self.grip_state == GripState.LOOSE:
                    _duration = 1
                else:
                    _duration = 2
                for _ in range(_duration):
                    await asyncio.sleep(1)
                self.grip_state = GripState.RELEASED

    async def _drive(self) -> None:
        while self._server.running:
            print("BEEP")
            await asyncio.sleep(1)
            if self.grip_state == GripState.ENGAGED:
                while self.speed < self._route.winder.speed:
                    await asyncio.sleep(1)
                    self.speed += self._acceleration
                    self.position += self.speed
                    self.location = self._route.where_am_i(self.position)
                self.position += self.speed
                self.location = self._route.where_am_i(self.position)
            elif self.speed > 0:
                while self.speed > 0:
                    await asyncio.sleep(1)
                    self.position += self.speed
                    self.location = self._route.where_am_i(self.position)
                    self.speed -= self._acceleration
