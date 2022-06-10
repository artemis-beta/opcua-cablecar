import typing

import cablecar.power as cab_power


class Route:
    def __init__(self, winder: cab_power.Winder) -> None:
        self._winder = winder
        self._call_points: typing.Dict[float, str] = {}
        self._let_go_points: typing.Dict[float, float] = {}

    @property
    def winder(self) -> cab_power.Winder:
        return self._winder

    @property
    def length(self) -> float:
        return max(self._call_points.keys())

    def add_stop(self, stop_name: str, distance: float) -> None:
        self._call_points[distance] = stop_name

    def __str__(self) -> str:
        _loc_template = "{distance:>10}   O   {name:10}\n"
        _out_str = f"{'Distance/m':>10}        {'Location':<10}\n"
        for i, (distance, place) in enumerate(self._call_points.items()):
            _out_str += _loc_template.format(distance=distance, name=place)
            if i + 1 < len(self._call_points):
                _out_str += f"{'':>10}   |   {'':>20}\n"
        return _out_str

    def where_am_i(self, position: float) -> typing.Tuple[str, str]:
        _out_loc: typing.List[str] = list(self._call_points.values())[:3]
        for distance, poi in self._call_points.items():
            if position > distance:
                _out_loc[0] = _out_loc[1]
                _out_loc[1] = poi
        return (_out_loc[0], _out_loc[1])


if __name__ in "__main__":
    x = Route()
    x.add_stop("A", 0)
    x.add_stop("B", 1.0)
    x.add_stop("C", 3.4)
    x.add_stop("D", 5.6)
    print(x)
