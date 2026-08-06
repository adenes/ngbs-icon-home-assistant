from pyModbusTCP.client import ModbusClient
import asyncio
import logging
import time

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class NGBSController:
    _base_address = 0x0100
    _modbus_client = None
    _thermostats = []
    _water_temperature = 0.0
    _cached_status = None
    _cached_temps = None
    _cached_humidity = None
    _last_update_time = 0.0

    def __init__(self, hass: HomeAssistant, host: str, port: int):
        self._hass = hass
        self._host = host
        self._port = port
        self._lock = asyncio.Lock()

    async def initialize(self):
        self._modbus_client = ModbusClient(
            host=self._host, port=self._port, auto_open=True
        )

        thermostats = await self.read_register(0x0008) or 0
        self._thermostats = []
        for index in range(8):
            if thermostats & 1 == 0:
                self._thermostats += [NGBSThermostat(self, index)]
            thermostats >>= 1

    def get_thermostats(self):
        return self._thermostats

    async def async_test_connection(self) -> bool:
        """Attempt to connect to the device and read a register.

        Used by the config flow to validate host/port before creating
        the config entry. Returns True on a successful read, False
        otherwise.
        """
        if self._modbus_client is None:
            self._modbus_client = ModbusClient(
                host=self._host, port=self._port, auto_open=True, timeout=5
            )
        return await self.read_register(0x0008) is not None

    async def read_register(self, address) -> int:
        x = await self.read_registers(address, 1)
        if x is None:
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

    async def write_register(self, address, value: int) -> bool:
        async with self._lock:
            res = await self._hass.async_add_executor_job(
                self._modbus_client.write_single_register,
                self._base_address + address,
                value,
            )
            if not res:
                res = await self._hass.async_add_executor_job(
                    self._modbus_client.write_multiple_registers,
                    self._base_address + address,
                    [value],
                )
            if not res:
                _LOGGER.error(
                    "Failed to write Modbus register 0x%04X with value %s",
                    self._base_address + address,
                    value,
                )
            return bool(res)

    async def update(self):
        now = time.monotonic()
        if now - self._last_update_time < 2.0 and self._cached_status is not None:
            return

        status_regs = await self.read_registers(0x0000, 18)
        if status_regs is not None:
            self._cached_status = status_regs
            if len(status_regs) > 17 and status_regs[17] is not None:
                self._water_temperature = float(status_regs[17]) / 10

        temps = await self.read_registers(0x0019, 8)
        if temps is not None:
            self._cached_temps = temps

        humidities = await self.read_registers(0x0021, 8)
        if humidities is not None:
            self._cached_humidity = humidities

        self._last_update_time = now

    def get_water_temperature(self):
        return self._water_temperature


class NGBSThermostat:
    def __init__(self, controller: NGBSController, index: int):
        self._controller = controller
        self._index = index
        self._current_temperature = 0.0
        self._humidity = 0.0
        self._target_temperatures = [0.0, 0.0, 0.0, 0.0]
        self._last_target_temp_write_time = [0.0, 0.0, 0.0, 0.0]
        self._last_eco_write_time = 0.0
        self._last_cooling_write_time = 0.0
        self._cooling = False
        self._eco = False
        self._idle = False

    def get_index(self):
        return self._index

    def get_unique_id(self):
        return "ngbs_thermostat_" + str(self._index)

    def get_controller(self):
        return self._controller

    def _get_temperature_offset(self):
        # HEATING  NORMAL  -> +0
        # COOLING  NORMAL  -> +1
        # HEATING  ECO     -> +2
        # COOLING  ECO     -> +3
        ret = 0
        if self._eco:
            ret += 2
        if self._cooling:
            ret += 1
        return ret

    def get_target_temperature(self) -> float:
        offset = self._get_temperature_offset()
        return self._target_temperatures[offset]

    async def set_target_temperature(self, temperature: float):
        offset = self._get_temperature_offset()
        addr = 0x0083 + (self._index * 4) + offset

        normalized_temp = int(round(temperature * 10))
        success = await self._controller.write_register(addr, normalized_temp)
        if success:
            new_temp = float(normalized_temp) / 10
            self._target_temperatures[offset] = new_temp
            self._last_target_temp_write_time[offset] = time.monotonic()

    def get_current_temperature(self):
        return self._current_temperature

    def get_humidity(self):
        return self._humidity

    def is_cooling(self):
        return self._cooling

    async def set_hvac_mode(self, cooling: bool):
        self._cooling = cooling
        self._last_cooling_write_time = time.monotonic()
        await self._controller.write_register(0x00B0 + self._index, 1 if cooling else 0)
        await self._controller.write_register(0x0062, 1 if cooling else 0)

    def is_eco(self):
        return self._eco

    async def set_eco(self, eco: bool):
        success = await self._controller.write_register(
            0x0063 + self._index, 1 if eco else 0
        )
        if success:
            self._eco = eco
            self._last_eco_write_time = time.monotonic()

    def is_idle(self):
        return self._idle

    async def update(self):
        await self._controller.update()

        ctrl = self._controller
        idx = self._index

        if ctrl._cached_temps is not None and idx < len(ctrl._cached_temps):
            val = ctrl._cached_temps[idx]
            if val is not None:
                self._current_temperature = float(val) / 10

        if ctrl._cached_humidity is not None and idx < len(ctrl._cached_humidity):
            val = ctrl._cached_humidity[idx]
            if val is not None:
                self._humidity = float(val) / 10

        target_temperatures = await ctrl.read_registers(0x0031 + 4 * idx, 4)
        if target_temperatures is not None:
            now = time.monotonic()
            for t_idx in range(4):
                read_val = float(target_temperatures[t_idx]) / 10
                if (
                    now - self._last_target_temp_write_time[t_idx] < 15.0
                    and read_val != self._target_temperatures[t_idx]
                ):
                    continue
                self._target_temperatures[t_idx] = read_val

        st = ctrl._cached_status
        if st is not None:
            now = time.monotonic()

            if len(st) > 4 and st[4] is not None:
                read_eco = ((st[4] >> idx) & 1) == 1
                if not (now - self._last_eco_write_time < 15.0 and read_eco != self._eco):
                    self._eco = read_eco

            if len(st) > 6 and st[6] is not None:
                read_cooling = ((st[6] >> idx) & 1) == 1
                if not (now - self._last_cooling_write_time < 15.0 and read_cooling != self._cooling):
                    self._cooling = read_cooling

            if len(st) > 10:
                regA = st[0] or 0
                regB = st[1] or 0
                relay = st[10] or 0
                heating_demand = (((regA >> idx) & 1) == 1) or (((relay >> idx) & 1) == 1)
                cooling_demand = (((regB >> idx) & 1) == 1) or (((relay >> (idx + 8)) & 1) == 1)
                self._idle = not (heating_demand or cooling_demand)
