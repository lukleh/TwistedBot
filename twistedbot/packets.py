
# original version from https://github.com/MostAwesomeDude/bravo

from StringIO import StringIO

from collections import namedtuple
from codecs import register
from codecs import (BufferedIncrementalDecoder, CodecInfo, IncrementalEncoder,
                    StreamReader, StreamWriter, utf_16_be_encode,
                    utf_16_be_decode)


from construct import Struct, Container, Embed, MetaField, Value
from construct import MetaArray, If, IfThenElse, Switch, Const, Peek
from construct import OptionalGreedyRange, RepeatUntil
from construct import Flag, PascalString, Adapter
from construct import UBInt8, UBInt16, UBInt32
from construct import SBInt8, SBInt16, SBInt32, SBInt64
from construct import BFloat32, BFloat64
from construct import BitStruct, BitField
from construct import StringAdapter, LengthValueAdapter, Sequence

from pynbt import NBTFile

import logbot

# Strings.
# This one is a UCS2 string, which effectively decodes single writeChar()
# invocations. We need to import the encoding for it first, though.

log = logbot.getlogger("BOT_ENTITY")


def ucs2(name):
    if name.lower() not in ("ucs2", "ucs-2"):
        return None

    def ucs2_encode(data, errors="replace"):
        data = u"".join(i if ord(i) < 65536 else u"?" for i in data)
        return utf_16_be_encode(data, errors)

    ucs2_decode = utf_16_be_decode

    class UCS2IncrementalEncoder(IncrementalEncoder):
        def encode(self, input, final=False):
            return ucs2_encode(input, self.errors)[0]

    class UCS2IncrementalDecoder(BufferedIncrementalDecoder):
        _buffer_decode = ucs2_decode

    class UCS2StreamWriter(StreamWriter):
        encode = ucs2_encode

    class UCS2StreamReader(StreamReader):
        decode = ucs2_decode

    return CodecInfo(
        name="ucs2",
        encode=ucs2_encode,
        decode=ucs2_decode,
        incrementalencoder=UCS2IncrementalEncoder,
        incrementaldecoder=UCS2IncrementalDecoder,
        streamwriter=UCS2StreamWriter,
        streamreader=UCS2StreamReader,
    )

register(ucs2)


class DoubleAdapter(LengthValueAdapter):

    def _encode(self, obj, context):
        return len(obj) / 2, obj


def AlphaString(name):
    return StringAdapter(
        DoubleAdapter(
            Sequence(name,
                     UBInt16("length"),
                     MetaField("data", lambda ctx: ctx["length"] * 2),
                     )
        ),
        encoding="ucs2",
    )

# Boolean converter.


def Bool(*args, **kwargs):
    return Flag(*args, default=True, **kwargs)

# Flying, position, and orientation, reused in several places.
grounded = Struct("grounded", UBInt8("grounded"))
position = Struct("position",
                  BFloat64("x"),
                  BFloat64("y"),
                  BFloat64("stance"),
                  BFloat64("z")
                  )
orientation = Struct("orientation", BFloat32("yaw"), BFloat32("pitch"))


def ByteString(name, size_name, encoding=None):
    return StringAdapter(MetaField("data", lambda ctx: ctx[size_name]),
                         encoding=encoding)


class NBTAdapter(Adapter):

    def _decode(self, obj, context):
        return NBTFile(StringIO(obj), compression=NBTFile.Compression.GZIP)


def NBTdata(name, size_name):
    return NBTAdapter(MetaField(name, lambda ctx: ctx[size_name]))


# item packing
slotdata = Struct("slotdata",
                  SBInt16("id"),
                  If(lambda context: context["id"] >= 0,
                     Embed(Struct("item_information",
                                  UBInt8("count"),
                                  UBInt16("damage"),
                                  SBInt16("size"),
                                  If(lambda context: context["size"] >= 0,
                                     NBTdata("data", size_name="size")
                                     )
                                  ))
                     )
                  )


Metadata = namedtuple("Metadata", "type value")
metadata_types = ["byte", "short", "int", "float", "string16", "slotdata",
                  "int_tup"]

# Metadata adaptor.


class MetadataAdapter(Adapter):

    def _decode(self, obj, context):
        d = {}
        for m in obj.data:
            d[m.id.identifier] = Metadata(metadata_types[m.id.data_type], m.value)
        return d

    def _encode(self, obj, context):
        c = Container(data=[], terminator=None)
        for k, v in obj.iteritems():
            t, value = v
            d = Container(
                id=Container(data_type=metadata_types.index(t), identifier=k),
                value=value,
                peeked=None)
            c.data.append(d)
        c.data[-1].peeked = 127
        return c

# Metadata inner container.
metadata_switch = {
    0: SBInt8("value"),
    1: SBInt16("value"),
    2: SBInt32("value"),
    3: BFloat32("value"),
    4: AlphaString("value"),
    5: slotdata,
    6: Struct("int_tup",
              SBInt32("x"),
              SBInt32("y"),
              SBInt32("z"),
              ),
}

# Metadata subconstruct.
entity_metadata = MetadataAdapter(
    Struct("metadata",
           RepeatUntil(lambda obj, context: obj["peeked"] == 0x7f,
                       Struct("data",
                              BitStruct("id",
                                        BitField("data_type", 3),  # first
                                        BitField("identifier", 5),  # second
                                        ),
                              Switch("value",
                                     lambda context: context["id"]["data_type"],
                                     metadata_switch),
                              Peek(SBInt8("peeked")),
                              ),
                       ),
           Const(UBInt8("terminator"), 0x7f),
           ),
)


# The actual packet list.
packets = {
    0: Struct("keep alive",
              SBInt32("pid"),
              ),
    1: Struct("login request ",
              SBInt32("eid"),
              AlphaString("level_type"),
              SBInt8("game_mode"),
              SBInt8("dimension"),
              SBInt8("difficulty"),
              UBInt8("unused"),
              UBInt8("players"),
              ),
    2: Struct("handshake",
              UBInt8("protocol"),
              AlphaString("username"),
              AlphaString("server_host"),
              SBInt32("server_port"),
              ),
    3: Struct("chat message",
              AlphaString("message"),
              ),
    4: Struct("time update",
              SBInt64("timestamp"),
              SBInt64("daytime"),
              ),
    5: Struct("entity equipment",
              UBInt32("eid"),
              UBInt16("slot"),
              slotdata,
              ),
    6: Struct("spawn position",
              SBInt32("x"),
              SBInt32("y"),
              SBInt32("z"),
              ),
    7: Struct("use entity",
              UBInt32("eid"),
              UBInt32("target"),
              UBInt8("button"),
              ),
    8: Struct("update health",
              SBInt16("hp"),
              SBInt16("fp"),
              BFloat32("saturation"),
              ),
    9: Struct("respawn",
              SBInt32("dimension"),
              UBInt8("difficulty"),
              UBInt8("game_mode"),
              UBInt16("world_height"),
              AlphaString("level_type"),
              ),
    10: Struct("player", UBInt8("grounded")),
    11: Struct("player position", position, grounded),
    12: Struct("player look", orientation, grounded),
    13: Struct("player position&look", position, orientation, grounded),
    14: Struct("player digging",
               UBInt8("state"),
               SBInt32("x"),
               SBInt8("y"),
               SBInt32("z"),
               SBInt8("face"),
               ),
    15: Struct("player block placement",
               SBInt32("x"),
               UBInt8("y"),
               SBInt32("z"),
               SBInt8("face"),
               slotdata,
               SBInt8("cursor_x"),  # position of crosshair on block
               SBInt8("cursor_y"),
               SBInt8("cursor_z"),
               ),
    16: Struct("held item change",
               UBInt16("item"),
               ),
    17: Struct("use bed",
               UBInt32("eid"),
               UBInt8("unknown"),
               SBInt32("x"),
               UBInt8("y"),
               SBInt32("z"),
               ),
    18: Struct("animation",
               UBInt32("eid"),
               UBInt8("animation"),
               ),
    19: Struct("entity action",
               UBInt32("eid"),
               UBInt8("action"),
               ),
    20: Struct("spawn named entity",
               UBInt32("eid"),
               AlphaString("username"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               UBInt8("yaw"),
               UBInt8("pitch"),
               SBInt16("item"),
               entity_metadata,
               ),
    21: Struct("spawn dropped item",
               UBInt32("eid"),
               slotdata,
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               SBInt8("yaw"),
               SBInt8("pitch"),
               SBInt8("roll"),
               ),
    22: Struct("collect item",
               UBInt32("eid"),
               UBInt32("destination"),
               ),
    23: Struct("spawn object/vehicle",
               UBInt32("eid"),
               UBInt8("type"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               SBInt32("object_data"),
               If(lambda context: context["object_data"] != 0,
                  Struct("velocity",
                         UBInt16("x"),
                         UBInt16("y"),
                         UBInt16("z"),
                         ),
                  ),
               ),
    24: Struct("spawn mob",
               UBInt32("eid"),
               UBInt8("type"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               SBInt8("yaw"),
               SBInt8("pitch"),
               SBInt8("head_yaw"),
               UBInt16("velocity_z"),
               UBInt16("velocity_x"),
               UBInt16("velocity_y"),
               entity_metadata,
               ),
    25: Struct("spawn painting",
               UBInt32("eid"),
               AlphaString("title"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               UBInt32("direction"),
               ),
    26: Struct("spawn experience orb",
               UBInt32("eid"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               UBInt16("count"),
               ),
    28: Struct("entity velocity",
               UBInt32("eid"),
               SBInt16("dx"),
               SBInt16("dy"),
               SBInt16("dz"),
               ),
    29: Struct("destroy entity",
               SBInt8("count"),
               MetaArray(lambda ctx: ctx.count, UBInt32("eids")),
               ),
    30: Struct("entity",
               UBInt32("eid"),
               ),
    31: Struct("entity relative move",
               UBInt32("eid"),
               SBInt8("dx"),
               SBInt8("dy"),
               SBInt8("dz")
               ),
    32: Struct("entity look",
               UBInt32("eid"),
               UBInt8("yaw"),
               UBInt8("pitch")
               ),
    33: Struct("entity look and relative move",
               UBInt32("eid"),
               SBInt8("dx"),
               SBInt8("dy"),
               SBInt8("dz"),
               UBInt8("yaw"),
               UBInt8("pitch")
               ),
    34: Struct("entity teleport",
               UBInt32("eid"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               UBInt8("yaw"),
               UBInt8("pitch"),
               ),
    35: Struct("entity head look",
               UBInt32("eid"),
               UBInt8("yaw"),
               ),
    38: Struct("entity status",
               SBInt32("eid"),
               SBInt8("status"),
               ),
    39: Struct("attach entity",
               UBInt32("eid"),
               UBInt32("vid"),
               ),
    40: Struct("entity metadata",
               UBInt32("eid"),
               entity_metadata,
               ),
    41: Struct("entity effect",
               UBInt32("eid"),
               UBInt8("effect"),
               UBInt8("amount"),
               UBInt16("duration"),
               ),
    42: Struct("remove entity effect",
               UBInt32("eid"),
               UBInt8("effect"),
               ),
    43: Struct("set experience",
               BFloat32("current"),
               UBInt16("level"),
               UBInt16("total"),
               ),
    51: Struct("chunk data",
               SBInt32("x"),
               SBInt32("z"),
               Bool("continuous"),
               UBInt16("primary_bitmap"),
               UBInt16("add_bitmap"),
               SBInt32("size"),
               #ByteString("data", size_name="size", encoding="zlib"),
               MetaField("data", lambda ctx: ctx["size"]),
               ),
    52: Struct("multi block change",
               SBInt32("x"),
               SBInt32("z"),
               UBInt16("count"),
               SBInt32("datasize"),
               MetaArray(lambda ctx: ctx.count,
                         BitStruct("blocks",
                                   BitField("x", 4),
                                   BitField("z", 4),
                                   BitField("y", 8),
                                   BitField("block_id", 12),
                                   BitField("meta", 4),
                                   )
                         ),
               ),
    53: Struct("block change",
               SBInt32("x"),
               UBInt8("y"),
               SBInt32("z"),
               UBInt16("type"),
               UBInt8("meta"),
               ),
    54: Struct("block action",
               SBInt32("x"),
               SBInt16("y"),
               SBInt32("z"),
               UBInt8("byte1"),
               UBInt8("byte2"),
               UBInt16("block_id"),
               ),
    55: Struct("block break animation",
               SBInt32("eid"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               UBInt8("distance"),
               ),
    56: Struct("map chunk bulk",
               SBInt16("count"),
               SBInt32("size"),
               #ByteString("data", size_name="size", encoding="zlib"),
               MetaField("data", lambda ctx: ctx["size"]),
               MetaArray(lambda ctx: ctx.count,
                         Struct("meta",
                                SBInt32("x"),
                                SBInt32("z"),
                                SBInt16("primary_bitmap"),
                                SBInt16("add_bitmap"),
                                )
                         ),
               ),
    60: Struct("explosion",
               BFloat64("x"),
               BFloat64("y"),
               BFloat64("z"),
               BFloat32("radius"),
               UBInt32("count"),
               MetaArray(lambda context: context.count,
                         Struct("records",
                                SBInt8("x"),
                                SBInt8("y"),
                                SBInt8("z")
                                ),
                         ),
               BFloat32("unknown1"),
               BFloat32("unknown2"),
               BFloat32("unknown3"),
               ),
    61: Struct("sound/particle effect",
               UBInt32("sid"),
               SBInt32("x"),
               SBInt8("y"),
               SBInt32("z"),
               SBInt32("data"),
               Bool("volume_decrease"),
               ),
    62: Struct("named sound effect",
               AlphaString("sound_name"),
               SBInt32("x"),
               UBInt32("y"),
               SBInt32("z"),
               BFloat32("volume"),
               UBInt8("pitch"),
               ),
    70: Struct("change game state",
               UBInt8("state"),
               UBInt8("creative"),
               ),
    71: Struct("thunderbolt",
               UBInt32("eid"),
               Bool("unknown"),
               SBInt32("x"),
               SBInt32("y"),
               SBInt32("z"),
               ),
    100: Struct("open window",
                UBInt8("wid"),
                UBInt8("type"),
                AlphaString("title"),
                UBInt8("slots"),
                ),
    101: Struct("close window",
                UBInt8("wid"),
                ),
    102: Struct("click window",
                SBInt8("wid"),
                SBInt16("slot"),
                SBInt8("button"),
                SBInt16("token"),
                SBInt8("shift"),
                slotdata,
                ),
    103: Struct("set slot",
                SBInt8("wid"),
                SBInt16("slot"),
                slotdata,
                ),
    104: Struct("set window items",
                SBInt8("window_id"),
                SBInt16("length"),
                MetaArray(lambda context: context["length"], slotdata),
                ),
    105: Struct("update window property",
                UBInt8("wid"),
                UBInt16("bar"),
                UBInt16("progress"),
                ),
    106: Struct("confirm transaction",
                UBInt8("wid"),
                UBInt16("token"),
                Bool("acknowledged"),
                ),
    107: Struct("creative inventory action ",
                UBInt16("slot"),
                slotdata,
                ),
    108: Struct("enchant item",
                UBInt8("wid"),
                UBInt8("enchantment"),
                ),
    130: Struct("update sign",
                SBInt32("x"),
                UBInt16("y"),
                SBInt32("z"),
                AlphaString("line1"),
                AlphaString("line2"),
                AlphaString("line3"),
                AlphaString("line4"),
                ),
    131: Struct("item data",
                SBInt16("primary"),
                SBInt16("secondary"),
                PascalString("data", length_field=UBInt16("length")),
                ),
    132: Struct("update tile entity",
                SBInt32("x"),
                UBInt16("y"),
                SBInt32("z"),
                SBInt8("action"),
                SBInt16("size"),
                If(lambda context: context["size"] > 0,
                   NBTdata("nbt", "size")
                   ),
                ),
    200: Struct("increment statistics",
                UBInt32("sid"),
                UBInt8("count"),
                ),
    201: Struct("player list item",
                AlphaString("name"),
                Bool("online"),
                UBInt16("ping"),
                ),
    202: Struct("player abilities",
                UBInt8("flags"),
                Value("is_god", lambda ctx: ctx["flags"] & 1),
                Value("is_flying", lambda ctx: ctx["flags"] & 2),
                Value("can_fly", lambda ctx: ctx["flags"] & 4),
                Value("is_creative", lambda ctx: ctx["flags"] & 8),
                UBInt8("walking_speed"),
                UBInt8("flying_speed"),
                ),
    203: Struct("tab complete",
                AlphaString("text"),
                ),
    204: Struct("locale view distance",
                AlphaString("locale"),
                UBInt8("view_distance"),  # 0 0:far, 1:normal, 2:short, 3:tiny
                UBInt8("chat_flags"),  # 0 on, no colors
                UBInt8("difficulty"),  # 0 0-peacefull,easy, normal, 3-hard
                Bool("show_cape"),
                ),
    205: Struct("client statuses",
                UBInt8("status"),
                ),
    250: Struct("plugin message",
                AlphaString("channel"),
                PascalString("data", length_field=SBInt16("length")),
                ),
    252: Struct("encryption key response",
                UBInt16("shared_length"),
                MetaField("shared_secret", lambda ctx: ctx.shared_length),
                UBInt16("token_length"),
                MetaField("token_secret", lambda ctx: ctx.token_length),
                ),
    253: Struct("encryption key request",
                AlphaString("server_id"),
                UBInt16("public_key_length"),
                MetaField("public_key", lambda ctx: ctx.public_key_length),
                UBInt16("token_length"),
                MetaField("verify_token", lambda ctx: ctx.token_length),
                ),
    254: Struct("server list ping",
                UBInt8("magic_number"),
                ),
    255: Struct("disconnect/kick",
                AlphaString("message"),
                ),
}


def packet_stream_print_header(context):
    #log.msg("packet_stream_print_header %s" % context["header"])
    return context["header"]


def print_and_return(pv, rv):
    log.msg("packet_stream_print_header %s" % pv)
    return rv

switcher = If(lambda context: context["header"] != 252,
              Switch("payload", packet_stream_print_header, packets)
              )

packet_stream = Struct("packet_stream",
                       OptionalGreedyRange(
                           Struct("full_packet",
                                  UBInt8("header"),
                                  Switch("payload",
                                         packet_stream_print_header,
                                         packets),
                                  ),
                       ),
                       OptionalGreedyRange(
                           UBInt8("leftovers"),
                       ),
                       )


def parse_packets(bytestream):
    """
    Opportunistically parse out as many packets as possible from a raw
    bytestream.

    Returns a tuple containing a list of unpacked packet containers, and any
    leftover unparseable bytes.
    """

    container = packet_stream.parse(bytestream)

    l = [(i.header, i.payload) for i in container.full_packet]
    leftovers = "".join(chr(i) for i in container.leftovers)

    return l, leftovers

incremental_packet_stream = \
    Struct("incremental_packet_stream",
           Struct("full_packet",
                  UBInt8("header"),
                  IfThenElse("payload",
                             lambda context: context["header"] != 252,
                             Switch("payload",
                                    packet_stream_print_header,
                                    packets),
                             Value("payload", lambda _: "")
                             ),
                  ),
           OptionalGreedyRange(
               UBInt8("leftovers"),
           ),
           )


def parse_packets_incrementally(bytestream):
    """
    Parse out packets one-by-one, yielding a tuple of packet header and packet
    payload.

    This function returns a generator.

    This function will yield all valid packets in the bytestream up to the
    first invalid packet.

    :returns: a generator yielding tuples of headers and payloads
    """

    while bytestream:
        parsed = incremental_packet_stream.parse(bytestream)
        header = parsed.full_packet.header
        payload = parsed.full_packet.payload
        bytestream = "".join(chr(i) for i in parsed.leftovers)

        yield header, payload

packets_by_name = dict((v.name, k) for (k, v) in packets.iteritems())


def make_packet(packet, payload, template=None):
    """
    Constructs a packet bytestream from a packet header and payload.

    The payload should be passed as keyword arguments. Additional containers
    or dictionaries to be added to the payload may be passed positionally, as
    well.
    """

    if packet not in packets_by_name:
        log.err("Couldn't find packet name %s!" % packet)
        return ""

    header = packets_by_name[packet]
    container = Container(**payload)

    if template is None:
        template = packets[header]
    payload = template.build(container)
    return chr(header) + payload


def make_error_packet(message):
    """
    Convenience method to generate an error packet bytestream.
    """

    return make_packet("error", message=message)
