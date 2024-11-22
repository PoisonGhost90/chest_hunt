### Imports

from __future__ import annotations

from csv import writer as csvwriter
from decimal import Decimal
from enum import Enum, auto
from itertools import product
from typing import Sequence, TypeAlias

### Type Checking


_DecimalNew: TypeAlias = Decimal | float | str | tuple[int, Sequence[int], int]


### CONSTANTS


MAKE_CSV = True
SIG_FIGS = 4
ARMORY_RATE = 0.005


### Utility Functions


def format(x: Decimal, sig_figs: int):
    form = f"1.{'0' * (sig_figs - 1)}E{x.adjusted()}"
    return x.quantize(Decimal(form))


### Classes


# Stores Chest Types
class CHType(Enum):
    LOOT = auto()
    MIMIC = auto()
    SAVER = auto()
    DOUBLER = auto()


# Handles chesthunt state information
class CH:
    solved: dict[CH, CHValue] = {}

    def __init__(
        self,
        chests: _DecimalNew = 30,
        mimics: _DecimalNew = 4,
        savers: int = 0,
        saves: int = 0,
        ad: bool = False,
        csaves: int = 0,
        doublers: int = 0,
        doubles: int = 0,
        dd: bool = False,
        perfect: bool = False,
        armory: bool = True,
    ):
        # 2 doublers means x2 x2
        if doublers > 1:
            dd = True
            perfect = False

        # number of chests
        self.chests = Decimal(chests)
        # number of mimics
        self.mimics = Decimal(mimics)
        # savers left to grab
        self.savers = savers
        # saves left
        self.saves = saves
        # uses ad
        self.ad = ad
        # crystal saves left
        self.csaves = csaves
        # doublers left to grab
        self.doublers = doublers
        # doubles left
        self.doubles = doubles
        # uses x2 x2
        self.dd = dd
        # want perfect hunt
        self.perfect = perfect
        # has armory chests
        self.armory = armory

        # chase x2 saver
        self.chase = perfect

    def __eq__(self, other: object):
        if not isinstance(other, CH):
            return False
        return (
            self.chests,
            self.mimics,
            self.savers,
            self.saves,
            self.ad,
            self.csaves,
            self.doublers,
            self.doubles,
            self.dd,
            self.perfect,
            self.chase,
            self.armory,
        ) == (
            other.chests,
            other.mimics,
            other.savers,
            other.saves,
            other.ad,
            other.csaves,
            other.doublers,
            other.doubles,
            other.dd,
            other.perfect,
            other.chase,
            other.armory,
        )

    def __hash__(self):
        return hash(
            (
                self.chests,
                self.mimics,
                self.savers,
                self.saves,
                self.ad,
                self.csaves,
                self.doublers,
                self.doubles,
                self.dd,
                self.perfect,
                self.chase,
                self.armory,
            )
        )

    # Creates a copy of the ch state
    def copy(self):
        ch = CH(
            chests=self.chests,
            mimics=self.mimics,
            savers=self.savers,
            saves=self.saves,
            ad=self.ad,
            csaves=self.csaves,
            doublers=self.doublers,
            doubles=self.doubles,
            dd=self.dd,
            perfect=self.perfect,
            armory=self.armory,
        )
        ch.chase = self.chase
        return ch

    # Checks whether the chesthunt value is known or not
    def stop(self):
        doublers = 1 if self.doublers > 0 else 0
        nonloot = self.mimics + self.savers + doublers
        default = nonloot >= self.chests or self.chests <= 0
        # return default
        return self in CH.solved or default

    # Returns the value of the current chesthunt state
    def value(self):
        perfect = self.mimics >= self.chests and self.chests >= 0
        default = CHValue(perfect=int(perfect))
        # return default
        return CH.solved.get(self, default)

    # Returns the next chesthunt state after opening <type> chest
    def next(self, type: CHType):
        ch = self.copy()
        ch.chests -= 1
        if self.csaves > 0:
            ch.csaves -= 1

        match type:
            case CHType.LOOT:
                # double loot
                if self.doubles > 0:
                    ch.doubles -= 1
            case CHType.MIMIC:
                # kill mimic
                ch.mimics -= 1
                if self.csaves <= 0:
                    ch.saves -= 1
            case CHType.SAVER:
                # remove saver chest and gain saves
                ch.savers -= 1
                ch.saves += 1
                # double saver when not x2 x2
                if not self.dd and self.doubles > 0:
                    ch.saves += 1
                    ch.doubles -= 1
            case CHType.DOUBLER:
                # remove double chest and gain doubles
                ch.doublers -= 1
                ch.doubles += 1

                # AD_SAVER provides room for strategy
                # First chest x2, swap method, ignore when x2 x2
                if self.csaves > 1 and self.ad and not self.dd:
                    ch.chase = not self.perfect

        return ch

    # Returns the chance of opening <type> chest
    def chance(self, type: CHType):
        match type:
            case CHType.LOOT:
                return self._chance_loot()
            case CHType.MIMIC:
                return self._chance_mimic()
            case CHType.SAVER:
                return self.savers / self.chests
            case CHType.DOUBLER:
                return self._chance_doubler()

    def _chance_doubler(self):
        # AD allows us to avoid savers
        chests = self.chests - (self.savers if self.ad else 0)

        doublers = 1 if self.doublers > 0 else 0
        return doublers / chests

    def _chance_mimic(self):
        # AD allows us to avoid savers
        chests = self.chests - (self.savers if self.ad else 0)

        return self.mimics / chests

    def _chance_loot(self):
        # AD allows us to avoid savers
        savers = 0 if self.ad else self.savers
        chests = self.chests - (self.savers if self.ad else 0)

        doublers = 1 if self.doublers > 0 else 0
        return (chests - self.mimics - savers - doublers) / chests


# Storage for chesthunt value(s)
class CHValue:
    def __init__(
        self,
        loot: _DecimalNew = 0,
        perfect: _DecimalNew = 0,
        armory: _DecimalNew = 0,
    ):
        self.loot = Decimal(loot)
        self.perfect = Decimal(perfect)
        self.armory = Decimal(armory)

    def __str__(self):
        return f"({self.loot}, {self.perfect}, {self.armory})"

    def __add__(self, other: CHValue):
        return CHValue(
            self.loot + other.loot,
            self.perfect + other.perfect,
            self.armory + other.armory,
        )

    def __mul__(self, other: _DecimalNew):
        other = Decimal(other)
        return CHValue(
            self.loot * other, self.perfect * other, self.armory * other
        )

    def __rmul__(self, other: _DecimalNew):
        return self.__mul__(other)


### Behavior Functions


def calculate_value(ch: CH) -> CHValue:
    ## Recursive Stop
    # - Idiot Check
    # - Perfect Hunt
    # - Known Values
    # - Computed Values
    value = ch.value()
    if ch.stop():
        return value

    ## Saver
    # AD_SAVER provides room for strategy
    if ch.savers > 0:
        if ch.ad:
            # Perfect - chase double saver
            if ch.chase and ch.doubles > 0:
                return calculate_value(ch.next(CHType.SAVER))

            # Gains - open saver after crystals
            elif not ch.chase and ch.csaves <= 0:
                return calculate_value(ch.next(CHType.SAVER))

            # Else - open saver if no doubler to find
            elif ch.doublers <= 0:
                return calculate_value(ch.next(CHType.SAVER))
        else:
            value += ch.chance(CHType.SAVER) * calculate_value(
                ch.next(CHType.SAVER)
            )

    ## Double
    if ch.doublers > 0:
        value += ch.chance(CHType.DOUBLER) * calculate_value(
            ch.next(CHType.DOUBLER)
        )

    ## Mimic
    if ch.mimics > 0 and (ch.saves > 0 or ch.csaves > 0):
        value += ch.chance(CHType.MIMIC) * calculate_value(
            ch.next(CHType.MIMIC)
        )

    ## Loot
    gain = 2 if ch.doubles > 0 else 1
    armory = ARMORY_RATE if ch.armory else 0
    loot = 1 - armory
    value += ch.chance(CHType.LOOT) * gain * CHValue(loot=loot, armory=armory)
    value += ch.chance(CHType.LOOT) * calculate_value(ch.next(CHType.LOOT))

    # Add the current value as a solved state
    CH.solved[ch] = value
    return value


def make_csv():
    config_saver = [0, 1]
    config_ad = [0, 1]
    config_csaver = [0, 1, 2]
    config_doubler = [0, 1, 2]
    config_perfect = [0, 1]
    config_armory = [0, 1]

    with open("chest_hunt.csv", "w", newline="") as outfile:
        out = csvwriter(outfile)
        out.writerow(
            [
                "Average Loot Chests",
                "Perfect Hunt Rate",
                "Average Armory Chests",
                "Armory Chest",
                "Saver",
                "Crystal Saver",
                "Reinforced Crystal Saver",
                "x2",
                "x2 x2",
                "Ad Saver",
                "Want Perfect",
            ]
        )

        for config in product(
            config_perfect,
            config_ad,
            config_doubler,
            config_csaver,
            config_saver,
            config_armory,
        ):
            p = config[0]
            ad = config[1]
            d = config[2]
            cs = config[3]
            s = config[4]
            a = config[5]

            # Pointless / Impossible
            if ad > 0 and s < 1:
                continue  # need saver for ad
            if p > 0 and (ad < 1 or d != 1):
                continue  # need ad and double saver for perfect strategy

            ch = CH(
                savers=s,
                ad=ad > 0,
                csaves=cs,
                doublers=d,
                perfect=p > 0,
                armory=a > 0,
            )

            value = calculate_value(ch)
            value.loot += 3 * value.perfect * value.loot

            out.writerow(
                [
                    format(value.loot, SIG_FIGS),
                    format(value.perfect * 100, SIG_FIGS),
                    format(value.armory, SIG_FIGS),
                    a > 0,
                    s > 0,
                    cs > 0,
                    cs > 1,
                    d > 0,
                    d > 1,
                    ad > 0,
                    p > 0,
                    value.loot,
                    value.perfect,
                    value.armory,
                ]
            )


if __name__ == "__main__":
    ch = CH(savers=1, csaves=2, doublers=1, perfect=True, armory=True)
    ch_ad = ch.copy()
    ch_ad.ad = True

    value = calculate_value(ch)
    value_ad = calculate_value(ch_ad)

    # perfect hunts give an average of x3 gains
    # (after upgrades are finished)
    value.loot += 3 * value.perfect * value.loot
    value_ad.loot += 3 * value_ad.perfect * value_ad.loot

    loot_p = format(value.loot, SIG_FIGS)
    loot_ad_p = format(value_ad.loot, SIG_FIGS)

    perfect_p = format(value.perfect * 100, SIG_FIGS)
    perfect_ad_p = format(value_ad.perfect * 100, SIG_FIGS)

    armory_p = format(value.armory, SIG_FIGS)
    armory_ad_p = format(value_ad.armory, SIG_FIGS)

    print(f"Average Loot Chests: {loot_p} | {loot_ad_p}")
    print(f"Perfect Hunt Rate: {perfect_p}% | {perfect_ad_p}%")
    print(f"Average Armory Chests: {armory_p} | {armory_ad_p}")
    print(f"{value}")
    print(f"{value_ad}")

    if MAKE_CSV:
        make_csv()
