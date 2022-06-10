import asyncio
import enum
import logging
import typing

import asyncua.sync
import asyncua.ua

import cablecar
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
        self._controller_address: typing.Optional[str] = None
        self._acceleration: float = 0.1
        self._brake_factor: typing.Dict[Controller, float] = {
            Controller.RAIL_BRAKE_APPLY: 2,
            Controller.SHOE_BRAKE_APPLY: 3
        }

    @property
    def objects_node(self) -> asyncua.sync.SyncNode:
        return self._server.get_node(
            asyncua.ua.TwoByteNodeId(asyncua.ua.ObjectIds.ObjectsFolder)
        )

    @property
    def controller_address(self) -> typing.Optional[str]:
        return self._controller_address

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
            cablecar.enum_member_str(GripState.RELEASED)
        )

        self._objects["CURRENT_SPEED"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_SPEED"',
            f"Cable Car {self._number} Speed",
            0.0,
        )

        self._objects["RAIL_BRAKE"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_RAIL_BRAKE"',
            f"Cable Car {self._number} Rail Brake",
            False,
        )

        self._controller_address = f'ns={self._namespace};s="CABLECAR_{self._number}_CONTROLLER"'

        self._objects["CONTROLLER"] = self.objects_node.add_variable(
            self._controller_address,
            f"Cable Car {self._number} Controller",
            cablecar.enum_member_str(Controller.NONE)
        )
        self._objects["CONTROLLER"].set_writable()

        self._objects["BELL"] = self.objects_node.add_variable(
            f'ns={self._namespace};s="CABLECAR_{self._number}_BELL"',
            f"Cable Car {self._number} Bell",
            False,
        )

    @property
    def grip_state(self) -> GripState:
        return getattr(GripState, self._objects["GRIP_STATE"].get_value())

    @grip_state.setter
    @cablecar.ignore_no_change
    def grip_state(self, state: GripState) -> None:
        self._logger.info(f"GRIP_STATE={state}")
        self._objects["GRIP_STATE"].set_value(cablecar.enum_member_str(state))

    @property
    def rail_brake(self) -> bool:
        return self._objects["RAIL_BRAKE"].get_value()

    @rail_brake.setter
    @cablecar.ignore_no_change
    def rail_brake(self, set_on: bool) -> None:
        self._objects["RAIL_BRAKE"].set_value(set_on)

    @property
    def speed(self) -> float:
        return float(self._objects["CURRENT_SPEED"].get_value())

    @speed.setter
    @cablecar.ignore_no_change
    def speed(self, value: float) -> None:
        self._logger.info(f"CURRENT_SPEED={value}")
        self._objects["CURRENT_SPEED"].set_value(value)

    @property
    def controller(self) -> Controller:
        return getattr(Controller, self._objects["CONTROLLER"].get_value())

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
    @cablecar.ignore_no_change
    def position(self, distance: float) -> None:
        self._logger.info(f"CURRENT_POSITION={distance}")
        self._objects["CURRENT_POSITION"].set_value(distance)

    @location.setter
    @cablecar.ignore_no_change
    def location(self, location: str) -> None:
        self._logger.info(f"CURRENT_LOCATION={location}")
        self._objects["CURRENT_LOCATION"].set_value(location)

    async def _check_bell_trigger(self) -> None:
        while self._server.running:
            await asyncio.sleep(0.5)
            if self.controller == Controller.BELL_RING:
                await self.ring_bell()

    async def _check_rail_brake(self) -> None:
        while self._server.running:
            await asyncio.sleep(0.5)
            if self.controller == Controller.RAIL_BRAKE_APPLY:
                # In reality the driver would need to ensure
                # the grip is released during braking
                # in the simulation do this automatically
                self.grip_state = GripState.RELEASED
                self.rail_brake = True

    async def _check_grip_trigger(self) -> None:
        while self._server.running:
            await asyncio.sleep(0.5)
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
            await asyncio.sleep(1)
            if self.position < 0.0 or self.position > self._route.length and abs(self.speed) > 0:
                self._logger.info("Reached route limit, stopping")
                self.grip_state = GripState.RELEASED
                self.controller = Controller.NONE
                self.speed = 0.0
                self.position = 0.0 if self.position < 0.0 else self._route.length
                continue
            elif self.grip_state == GripState.ENGAGED:
                while abs(self.speed) < abs(self._route.winder.speed):
                    await asyncio.sleep(1)
                    self.speed += self._acceleration if self._route.winder.speed > 0 else -self._acceleration
                    self.position += self.speed if self._route.winder.speed > 0 else -self.speed
                    self.location = self._route.where_am_i(self.position)
                self.position += self.speed
                self.location = self._route.where_am_i(self.position)
            elif abs(self.speed) > 0:
                _total_deceleration: float = self._acceleration
                if self.rail_brake:
                    _total_deceleration *= self._brake_factor[Controller.RAIL_BRAKE_APPLY]
                while abs(self.speed) > 0:
                    await asyncio.sleep(1)
                    self.position += self.speed if self._route.winder.speed > 0 else -self.speed
                    self.location = self._route.where_am_i(self.position)
                    self.speed -= _total_deceleration
