import asyncio
import logging
import typing

import click

logging.basicConfig()

import cablecar.car as cab_car
import cablecar.configs as cab_config
import cablecar.power as cab_power
import cablecar.route as cab_route
import cablecar.server as cab_server


class Simulation:
    def __init__(self, configuration: str = "powell") -> None:
        self._label: str = configuration.title()
        self._config: typing.Dict[str, typing.Any] = getattr(
            cab_config.Configs(), configuration
        )
        self._server: typing.Optional[cab_server.SimulationServer] = None
        self._route: typing.Optional[cab_route.Route] = None
        self._winder: typing.Optional[cab_power.Winder] = None
        self._cars: typing.List[cab_car.CableCar] = []

    def __enter__(self) -> "Simulation":
        self._server = cab_server.SimulationServer()
        self._server.start()
        self._setup_route()
        return self

    def __exit__(self, *args, **kwargs) -> None:
        asyncio.run(self._server.stop())

    def _setup_route(self) -> None:
        self._winder = cab_power.Winder(self._label, self._server)
        self._route = cab_route.Route(self._winder)

    def add_car(self) -> None:
        self._cars.append(cab_car.CableCar(len(self._cars) + 1))
        self._cars[-1].add_to_route(self._route)

    def run_simulation(self) -> None:
        asyncio.run(self._server.launch())


@click.command
def simulate() -> None:
    with Simulation() as cabsim:
        cabsim.add_car()
        cabsim.run_simulation()
