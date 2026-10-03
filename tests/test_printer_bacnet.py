"""Actual printer bytes through production C parser/observer/BACnet, offline only."""
import asyncio
import subprocess
from pathlib import Path
from bacpypes3.app import Application
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.pdu import Address

ROOT = Path(__file__).resolve().parents[1]


def test_captured_trouble_to_independent_bacnet(tmp_path):
    serial = tmp_path / 'fixture-bytes.txt'
    serial.write_bytes(b'')
    log = (tmp_path / 'native.log').open('w')
    process = subprocess.Popen([str(ROOT / 'build-tests/printer_bacnet'),
                                str(ROOT / 'fixtures/printer-test-registry.json'),
                                str(serial), '47838'], stdout=log, stderr=log)

    async def check():
        args = SimpleArgumentParser().parse_args(['--address', '127.0.0.1:47839',
                 '--instance', '3899998', '--name', 'Independent printer fixture client'])
        app = Application.from_args(args)
        dst = '127.0.0.1:47838'

        async def state(expected):
            for _ in range(20):
                values = await app.read_property_multiple(Address(dst), ['binary-input,106',
                    ['present-value', 'reliability', 'status-flags'], 'binary-input,109', ['present-value']])
                if str(values[0][3]) == expected:
                    break
                await asyncio.sleep(.05)
            assert str(values[0][3]) == expected
            assert str(values[1][3]) == 'communication-failure'
            assert values[2][3]['fault']
            assert str(values[3][3]) == 'inactive'
            for instance in (105, 107, 108):
                assert str(await app.read_property(dst, f'binary-input,{instance}', 'present-value')) == 'inactive'
                assert str(await app.read_property(dst, f'binary-input,{instance}', 'reliability')) == 'communication-failure'

        async def send(frame):
            with serial.open('ab') as f:
                f.write(frame)
            await asyncio.sleep(.15)

        try:
            await asyncio.sleep(.3)
            assert len(await app.who_is(3899001, 3899001, Address(dst), timeout=1)) == 1
            await state('inactive')
            frames = (ROOT / 'fixtures/printer-trouble-sanitized.txt').read_bytes().split(b'\r\n\r\n')
            common = [b'\r\n'+f+b'\r\n\r\n' for f in frames if b'COMMON TRBL' in f]
            assert len(common) == 6
            await send(common[0]); await state('active')
            await send(common[1]); await state('inactive')
            await send(common[0]); await state('inactive')  # older ACT cannot replace RST
            await send(common[2]); await state('active')
            await send(b'\r\nunknown record\r\n\r\n'); await state('active')
            await send(common[3][:-4]); await state('active')  # incomplete restore
            await send(b'\r\n\r\n'); await state('inactive')
            await send(common[4]); await state('active')
            await send(common[5]); await state('inactive')
            assert int(await app.read_property(dst, 'device,3899001', 'object-list', 0)) == 15
        finally:
            app.close()

    try:
        asyncio.run(check())
    finally:
        process.terminate(); process.wait(timeout=5); log.close()
    assert 'AddressSanitizer' not in (tmp_path / 'native.log').read_text()
