import asyncio
import click
import logging

logging.basicConfig()

import cablecar.server as cab_server
import cablecar.car as cab_car
import cablecar.route as cab_route
import cablecar.power as cab_power


@click.command()
def simulate() -> None:
    logging.getLogger("CableCarSim").setLevel(logging.INFO)
    with cab_server.SimulationServer() as server:
        _logger = logging.getLogger("CableCarSim.Simulation")
        _logger.info("Setting up simulation")
        _winder = cab_power.Winder("Powell", server)
        _route = cab_route.Route(_winder)
        _route.add_stop("Hyde St & Beach St", 0)
        _route.add_stop("Hyde St & North Point St", 50)
        _route.add_stop("Hyde St & Bay St", 100)
        _route.add_stop("Hyde St & Chestnut St", 150)
        _route.add_stop("Hyde St & Lombard St", 200)
        _route.add_stop("Hyde St & Greenwich St", 250)
        _route.add_stop("Hyde St & Filbert St", 300)
        _route.add_stop("Hyde St & Union St", 350)
        _route.add_stop("Hyde St & Green St", 400)
        _route.add_stop("Hyde St & Vallejo St", 450)
        _route.add_stop("Hyde St & Broadway", 500)
        _route.add_stop("Hyde St & Pacific Ave", 550)
        _route.add_stop("Hyde St & Jackson St", 600)
        _route.add_stop("Washington St & Leavenworth St", 650)
        _route.add_stop("Washington St & Jones St", 700)
        _route.add_stop("Washington St & Taylor St", 750)
        _route.add_stop("Washington St & Mason St", 800)
        _route.add_stop("Washington St & Powell St", 850)
        _route.add_stop("Powell St & Clay St", 900)
        _route.add_stop("Powell St & Sacramento St", 950)
        _route.add_stop("Powell St & California St", 1000)
        _route.add_stop("Powell St & Pine St", 1050)
        _route.add_stop("Powell St & Bush St", 1100)
        _route.add_stop("Powell St & Sutter St", 1150)
        _route.add_stop("Powell St & Post St", 1200)
        _route.add_stop("Powell St & Geary St", 1250)
        _route.add_stop("Powell St & O'Farrell St", 1300)
        _route.add_stop("Powell St & Market St", 1350)

        _car = cab_car.CableCar(1)
        _car.add_to_route(_route)

        asyncio.run(server.launch())
