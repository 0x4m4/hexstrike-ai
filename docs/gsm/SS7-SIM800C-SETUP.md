# SS7 + SIM800C — архитектура и настройка

## Главное

**SIM800C не подключается к SS7 напрямую.** Это разные уровни:

| Компонент | Протокол | Интерфейс | Назначение |
|-----------|----------|-----------|------------|
| SIM800C | GSM 2G, AT-команды | UART (TXD/RXD) | SMS, голос, GPRS, USSD |
| SS7 (Osmocom) | M3UA/SCCP/SIGTRAN | SCTP :2905 | Сигнализация в ядре сети (лаборатория) |

Если раньше «всё работало», скорее всего у вас была **двухчастная** схема:
- **SIM800C** — для GSM (SMS/регистрация в сети)
- **Отдельный SS7-стек** (Osmocom, коммерческий шлюз) — для сигнализации

## Быстрый старт

### На Mac (iMac) — SIM800C

```bash
cd /Volumes/Eva/mufasaai-storage/hexstrike-ai   # или ваш путь к репо
bash scripts/gsm/setup-sim800c-mac.sh
```

Если порт известен:
```bash
SIM800C_PORT=/dev/cu.usbserial-1410 SIM800C_BAUD=115200 \
  bash scripts/gsm/setup-sim800c-mac.sh
```

**На Mac используйте `/dev/cu.*`, не `/dev/tty.*`** — иначе порт может зависнуть.

### SS7 на Mac (через VPS)

Osmocom SS7 не работает нативно на macOS (нужен SCTP/Linux):

```bash
bash scripts/gsm/setup-ss7-mac.sh          # SIM800C на Mac + инструкции
bash scripts/gsm/setup-ss7-mac.sh --vps    # SS7-стек на Linux VPS
```

### На Linux с подключённым SIM800C

```bash
cd /path/to/hexstrike-ai
bash scripts/gsm/setup-sim800c.sh
```

Результат: `artifacts/gsm/sim800c-diagnose.json`

### SS7-лаборатория (Linux, нужен SCTP)

```bash
bash scripts/gsm/setup-ss7-lab.sh
# или всё сразу:
bash scripts/gsm/setup-all.sh
```

### Ручная проверка AT

```bash
# Linux
minicom -D /dev/ttyUSB0 -b 115200

# Mac
minicom -D /dev/cu.usbserial-XXXX -b 115200
```

Команды:
```
AT          → OK
AT+CPIN?    → +CPIN: READY
AT+CSQ      → уровень сигнала
AT+CREG?    → +CREG: 0,1 (зарегистрирован)
```

## Подключение SIM800C

```
SIM800C          USB-TTL (3.3V!)
────────         ────────────────
VCC (4.0V)   →   отдельный БП 4V/2A (НЕ 5V на логику)
GND          →   GND
TXD          →   RXD адаптера
RXD          →   TXD адаптера
ANT          →   GSM-антенна 50Ω
```

## Типичные проблемы

| Симптом | Решение |
|---------|---------|
| Нет `/dev/ttyUSB*` | Драйвер CH340/CP2102, кабель, `dmesg` |
| `AT` без ответа | Baud 115200/9600, перепутаны TX/RX, питание 4V |
| `+CPIN: SIM PIN` | `AT+CPIN="1234"` |
| `+CREG: 0,0` | Антенна, 2G отключён оператором — другая SIM |
| SS7 M3UA fail | `sudo modprobe sctp`, нужен Linux с lksctp |

## Ограничения Cloud Agent

Cursor Cloud Agent **не видит USB-устройства**. SIM800C нужно диагностировать на **вашем Mac** или **VPS** с физическим подключением модуля.

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/gsm/setup-sim800c-mac.sh` | **Mac**: драйверы + AT-диагностика |
| `scripts/gsm/setup-ss7-mac.sh` | **Mac**: SIM800C + SS7 через VPS |
| `scripts/gsm/setup-sim800c.sh` | Linux: драйверы + AT-диагностика |
| `scripts/gsm/sim800c_diagnose.py` | Автопоиск порта и baud |
| `scripts/gsm/setup-ss7-lab.sh` | Linux: Osmocom STP/HLR/MSC |
| `scripts/gsm/setup-all.sh` | Оба шага (Linux) |
