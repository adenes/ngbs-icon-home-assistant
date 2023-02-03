from pyModbusTCP.client import ModbusClient
import asyncio

from homeassistant.core import HomeAssistant


class NGBSController:
    _base_address = 0x0100
    _modbus_client = None
    _thermostats = []
    _water_temperature = 0.0

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        self._hass = hass
        self._host = host
        self._port = port
        self._lock = asyncio.Lock()

    async def initialize(self):
        self._modbus_client = ModbusClient(
            host=self._host, port=self._port, auto_open=True
        )

        thermostats = await self.read_register(0x0008)
        self._thermostats = []
        for index in range(8):
            if thermostats & 1 == 0:
                self._thermostats += [NGBSThermostat(self, index)]
            thermostats >>= 1

    def get_thermostats(self):
        return self._thermostats

    async def read_register(self, address) -> int:
        x = await self.read_registers(address, 1)
        if x == None:
            return None
        else:
            return x[0]

    async def read_registers(self, address, count):
        async with self._lock:
            ret = await self._hass.async_add_executor_job(
                self._read_modbus_holding_registers, address, count
            )
        return ret

    def _read_modbus_holding_registers(self, address, count):
        return self._modbus_client.read_holding_registers(
            self._base_address + address, count
        )

    async def write_register(self, address, value: int):
        async with self._lock:
            await self._hass.async_add_executor_job(
                self._modbus_client.write_single_register,
                self._base_address + address,
                value,
            )
            await asyncio.sleep(5)

    async def update(self):
        water_temperature = await self.read_register(0x0011)
        if water_temperature:
            self._water_temperature = float(water_temperature) / 10

    def get_water_temperature(self):
        return self._water_temperature


class NGBSThermostat:
    _current_temperature = 0.0
    _humidity = 0.0
    _target_heating_normal = 0.0
    _target_cooling_normal = 0.0
    _target_heating_eco = 0.0
    _target_cooling_eco = 0.0
    _cooling = False
    _eco = False
    _idle = False

    def __init__(self, controller: NGBSController, index: int):
        self._controller = controller
        self._index = index

    def get_index(self):
        return self._index

    def get_unique_id(self):
        return "ngbs_thermostat_" + str(self._index)

    def get_controller(self):
        return self._controller

    def get_target_temperature(self) -> float:
        if self._cooling:
            if self._eco:
                return self._target_cooling_eco
            else:
                return self._target_cooling_normal
        else:
            if self._eco:
                return self._target_heating_eco
            else:
                return self._target_heating_normal

    async def set_target_temperature(self, temperature: float):
        addr = 0x0083 + (self._index * 4)
        # HEATING  NORMAL  -> +0
        # COOLING  NORMAL  -> +1
        # HEATING  ECO     -> +2
        # COOLING  ECO  -> +3
        if self._eco:
            addr += 2
        if self._cooling:
            addr += 1

        normalized_temp = int(temperature * 10)
        await self._controller.write_register(addr, normalized_temp)

    def get_current_temperature(self):
        return self._current_temperature

    def get_humidity(self):
        return self._humidity

    def is_cooling(self):
        return self._cooling

    def is_eco(self):
        return self._eco

    async def set_eco(self, eco: bool):
        await self._controller.write_register(0x0063 + self._index, 1 if eco else 0)

    def is_idle(self):
        return self._idle

    async def update(self):
        current_temperature = await self._controller.read_register(0x0019 + self._index)
        if current_temperature:
            self._current_temperature = float(current_temperature) / 10

        humidity = await self._controller.read_register(0x0021 + self._index)
        if humidity:
            self._humidity = float(humidity) / 10

        target_temperatures = await self._controller.read_registers(
            0x0031 + 4 * self._index, 4
        )

        if target_temperatures:
            [
                self._target_heating_normal,
                self._target_cooling_normal,
                self._target_heating_eco,
                self._target_cooling_eco,
            ] = [float(x) / 10 for x in target_temperatures]

        eco = await self._controller.read_register(0x0004)
        self._eco = eco >> self._index & 1 == 1 if eco else False

        cooling = await self._controller.read_register(0x0006)
        self._cooling = cooling >> self._index & 1 == 1 if cooling else False

        tmp = await self._controller.read_register(0x0000) or 0
        tmp |= await self._controller.read_register(0x0001) or 0
        self._idle = tmp >> self._index & 1 == 0
