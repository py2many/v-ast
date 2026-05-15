"""
JPEG parser in static-python style.

Parses marker/segment structure and extracts:
- frame dimensions/components from SOF
- JFIF metadata from APP0
- quantization and huffman table counts
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

type u8 = int
type u16 = int
type u32 = int
type i32 = int


class smt:
    @staticmethod
    def pre() -> bool:
        return __debug__

    @staticmethod
    def post(_value: object = None) -> bool:
        return __debug__


@dataclass(frozen=True)
class Ok[T]:
    value: T


@dataclass(frozen=True)
class Err[E]:
    error: E


type Result[T, E] = Ok[T] | Err[E]


def ok[T](value: T) -> Result[T, str]:
    return Ok(value)


def err[T](message: str) -> Result[T, str]:
    return Err(message)


SOI: u16 = 0xFFD8
EOI: u16 = 0xFFD9
SOS: u16 = 0xFFDA
APP0: u16 = 0xFFE0
DQT: u16 = 0xFFDB
DHT: u16 = 0xFFC4

SOF_MARKERS: frozenset[u16] = frozenset(
    [0xFFC0, 0xFFC1, 0xFFC2, 0xFFC3, 0xFFC5, 0xFFC6, 0xFFC7, 0xFFC9, 0xFFCA, 0xFFCB]
)

NO_PAYLOAD: frozenset[u16] = frozenset([SOI, EOI, 0xFFD0, 0xFFD1, 0xFFD2, 0xFFD3, 0xFFD4, 0xFFD5, 0xFFD6, 0xFFD7])


@dataclass
class Segment:
    offset: u32
    marker: u16
    length: u16
    payload: bytes


@dataclass
class FrameComponent:
    component_id: u8
    h_sampling: u8
    v_sampling: u8
    quant_table_id: u8


@dataclass
class FrameInfo:
    marker: u16
    precision: u8
    width: u16
    height: u16
    components: list[FrameComponent]


@dataclass
class JFIFInfo:
    version_major: u8
    version_minor: u8
    density_units: u8
    x_density: u16
    y_density: u16
    thumb_width: u8
    thumb_height: u8


@dataclass
class JpegInfo:
    path: str
    segments: list[Segment] = field(default_factory=list)
    frame: FrameInfo | None = None
    jfif: JFIFInfo | None = None
    dqt_tables: u32 = 0
    dht_tables: u32 = 0


@dataclass
class Reader:
    data: bytes
    pos: u32 = 0

    def remaining(self) -> u32:
        return len(self.data) - self.pos

    def read(self, n: u32) -> Result[bytes, str]:
        if smt.pre():
            assert n >= 0

        end = self.pos + n
        if end > len(self.data):
            return err(f"unexpected EOF at {self.pos}, wanted {n} bytes")
        out = self.data[self.pos : end]
        self.pos = end
        return ok(out)

    def read_u8(self) -> Result[u8, str]:
        match self.read(1):
            case Err(e):
                return Err(e)
            case Ok(b):
                return ok(b[0])

    def read_u16_be(self) -> Result[u16, str]:
        match self.read_u8():
            case Err(e):
                return Err(e)
            case Ok(hi):
                pass
        match self.read_u8():
            case Err(e):
                return Err(e)
            case Ok(lo):
                pass
        return ok((hi << 8) | lo)

    def peek_u8(self) -> Result[u8, str]:
        if self.pos >= len(self.data):
            return err("unexpected EOF in peek")
        return ok(self.data[self.pos])


def read_file(path: str | Path) -> Result[bytes, str]:
    try:
        data = Path(path).read_bytes()
    except OSError as e:
        return err(f"failed to read {path}: {e}")
    return ok(data)


def read_marker(reader: Reader) -> Result[u16, str]:
    if reader.remaining() < 2:
        return err("unexpected EOF before marker")

    match reader.read_u8():
        case Err(e):
            return Err(e)
        case Ok(first):
            if first != 0xFF:
                return err(f"expected marker prefix 0xFF, got 0x{first:02X} at offset {reader.pos - 1}")

    match reader.read_u8():
        case Err(e):
            return Err(e)
        case Ok(low):
            while low == 0xFF:
                match reader.read_u8():
                    case Err(e):
                        return Err(e)
                    case Ok(v):
                        low = v

    marker = (0xFF << 8) | low
    return ok(marker)


def skip_entropy_data(reader: Reader) -> Result[None, str]:
    while reader.remaining() >= 2:
        match reader.read_u8():
            case Err(e):
                return Err(e)
            case Ok(v):
                if v != 0xFF:
                    continue

        match reader.read_u8():
            case Err(e):
                return Err(e)
            case Ok(next_b):
                match next_b:
                    case 0x00:
                        continue
                    case 0xFF:
                        while reader.remaining() > 0:
                            match reader.peek_u8():
                                case Err(e):
                                    return Err(e)
                                case Ok(p):
                                    if p != 0xFF:
                                        break
                            reader.pos += 1
                        continue
                    case _:
                        reader.pos -= 2
                        return ok(None)
    return ok(None)


def next_segment(reader: Reader) -> Result[Segment | None, str]:
    if reader.remaining() == 0:
        return ok(None)

    offset = reader.pos
    match read_marker(reader):
        case Err(e):
            return Err(e)
        case Ok(marker):
            pass

    if marker in NO_PAYLOAD:
        return ok(Segment(offset=offset, marker=marker, length=0, payload=b""))

    match reader.read_u16_be():
        case Err(e):
            return Err(e)
        case Ok(length):
            if length < 2:
                return err(f"invalid segment length {length} for marker 0x{marker:04X}")
            payload_len = length - 2

    match reader.read(payload_len):
        case Err(e):
            return Err(e)
        case Ok(payload):
            seg = Segment(offset=offset, marker=marker, length=length, payload=payload)

    if marker == SOS:
        match skip_entropy_data(reader):
            case Err(e):
                return Err(e)
            case Ok(_):
                pass

    return ok(seg)


def parse_frame(marker: u16, payload: bytes) -> Result[FrameInfo, str]:
    if smt.pre():
        assert len(payload) >= 6

    r = Reader(payload)
    match r.read_u8():
        case Err(e):
            return Err(e)
        case Ok(precision):
            pass
    match r.read_u16_be():
        case Err(e):
            return Err(e)
        case Ok(height):
            pass
    match r.read_u16_be():
        case Err(e):
            return Err(e)
        case Ok(width):
            pass
    match r.read_u8():
        case Err(e):
            return Err(e)
        case Ok(count):
            pass

    components: list[FrameComponent] = []
    for _ in range(count):
        if r.remaining() < 3:
            return err("truncated SOF component entry")
        match r.read_u8():
            case Err(e):
                return Err(e)
            case Ok(cid):
                pass
        match r.read_u8():
            case Err(e):
                return Err(e)
            case Ok(sampling):
                h = (sampling >> 4) & 0x0F
                v = sampling & 0x0F
        match r.read_u8():
            case Err(e):
                return Err(e)
            case Ok(qid):
                pass
        components.append(FrameComponent(component_id=cid, h_sampling=h, v_sampling=v, quant_table_id=qid))

    frame = FrameInfo(marker=marker, precision=precision, width=width, height=height, components=components)
    if smt.post(frame):
        assert frame.width > 0
        assert frame.height > 0
        assert len(frame.components) == count
    return ok(frame)


def parse_app0(payload: bytes) -> Result[JFIFInfo | None, str]:
    if len(payload) < 14:
        return ok(None)
    if payload[0:5] != b"JFIF\x00":
        return ok(None)

    major = payload[5]
    minor = payload[6]
    units = payload[7]
    x_density = (payload[8] << 8) | payload[9]
    y_density = (payload[10] << 8) | payload[11]
    thumb_w = payload[12]
    thumb_h = payload[13]
    return ok(
        JFIFInfo(
            version_major=major,
            version_minor=minor,
            density_units=units,
            x_density=x_density,
            y_density=y_density,
            thumb_width=thumb_w,
            thumb_height=thumb_h,
        )
    )


def count_dqt_tables(payload: bytes) -> Result[u32, str]:
    r = Reader(payload)
    tables: u32 = 0
    while r.remaining() > 0:
        match r.read_u8():
            case Err(e):
                return Err(e)
            case Ok(info):
                precision = (info >> 4) & 0x0F
                if precision == 0:
                    size = 64
                elif precision == 1:
                    size = 128
                else:
                    return err(f"invalid DQT precision {precision}")
        match r.read(size):
            case Err(e):
                return Err(e)
            case Ok(_):
                tables += 1
    return ok(tables)


def count_dht_tables(payload: bytes) -> Result[u32, str]:
    r = Reader(payload)
    tables: u32 = 0
    while r.remaining() > 0:
        if r.remaining() < 17:
            return err("truncated DHT payload")
        match r.read_u8():
            case Err(e):
                return Err(e)
            case Ok(_):
                pass
        match r.read(16):
            case Err(e):
                return Err(e)
            case Ok(counts_raw):
                count_total: u32 = 0
                for b in counts_raw:
                    count_total += b
        match r.read(count_total):
            case Err(e):
                return Err(e)
            case Ok(_):
                tables += 1
    return ok(tables)


def parse_jpeg(path: str | Path) -> Result[JpegInfo, str]:
    match read_file(path):
        case Err(e):
            return Err(e)
        case Ok(raw):
            pass

    reader = Reader(raw)
    jpeg = JpegInfo(path=str(path))

    match next_segment(reader):
        case Err(e):
            return Err(e)
        case Ok(None):
            return err("empty file")
        case Ok(first):
            if first.marker != SOI:
                return err("missing SOI marker")
            jpeg.segments.append(first)

    while True:
        match next_segment(reader):
            case Err(e):
                return Err(e)
            case Ok(None):
                break
            case Ok(seg):
                jpeg.segments.append(seg)

                match seg.marker:
                    case m if m in SOF_MARKERS:
                        match parse_frame(seg.marker, seg.payload):
                            case Err(e):
                                return Err(e)
                            case Ok(frame):
                                jpeg.frame = frame
                    case m if m == APP0:
                        match parse_app0(seg.payload):
                            case Err(e):
                                return Err(e)
                            case Ok(jfif):
                                jpeg.jfif = jfif
                    case m if m == DQT:
                        match count_dqt_tables(seg.payload):
                            case Err(e):
                                return Err(e)
                            case Ok(n):
                                jpeg.dqt_tables += n
                    case m if m == DHT:
                        match count_dht_tables(seg.payload):
                            case Err(e):
                                return Err(e)
                            case Ok(n):
                                jpeg.dht_tables += n
                    case _:
                        pass

                if seg.marker == EOI:
                    break

    return ok(jpeg)


def marker_name(marker: u16) -> str:
    match marker:
        case m if m == SOI:
            return "SOI"
        case m if m == EOI:
            return "EOI"
        case m if m == SOS:
            return "SOS"
        case m if m == APP0:
            return "APP0"
        case m if m == DQT:
            return "DQT"
        case m if m == DHT:
            return "DHT"
        case m if m in SOF_MARKERS:
            return "SOF"
        case _:
            return f"0x{marker:04X}"


def print_report(info: JpegInfo) -> None:
    print(f"File: {info.path}")
    print(f"Segments: {len(info.segments)}")
    for seg in info.segments:
        size = f"{seg.length} B" if seg.length > 0 else "(none)"
        print(f"  0x{seg.marker:04X} {marker_name(seg.marker):<5} @0x{seg.offset:08X} {size}")

    if info.frame is not None:
        frame = info.frame
        print()
        print(f"Frame: {frame.width}x{frame.height}, {frame.precision}-bit, components={len(frame.components)}")
        for comp in frame.components:
            print(
                f"  C{comp.component_id}: sampling={comp.h_sampling}x{comp.v_sampling}, qtable={comp.quant_table_id}"
            )

    if info.jfif is not None:
        j = info.jfif
        print()
        print(
            f"JFIF: v{j.version_major}.{j.version_minor:02d} density={j.x_density}x{j.y_density} units={j.density_units}"
        )

    print()
    print(f"DQT tables: {info.dqt_tables}")
    print(f"DHT tables: {info.dht_tables}")


def main() -> i32:
    args = sys.argv[1:]
    if len(args) == 0:
        print("usage: jpeg_static_parser.py <file.jpg> [...]", file=sys.stderr)
        return 1

    all_ok = True
    for path in args:
        match parse_jpeg(path):
            case Err(e):
                print(f"error: {path}: {e}", file=sys.stderr)
                all_ok = False
            case Ok(info):
                print_report(info)
        print()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
