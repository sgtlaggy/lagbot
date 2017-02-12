# Overwatch Stat Commands

#### Note these commands may not give 100% accurate information due to [OWAPI](https://github.com/SunDwarf/OWAPI) being down or Blizzard changing how they format data or being a bit behind on real stats.

Valid tiers for unranked/quickplay are: `quick`, `quickplay`, `qp`, `general`, `unranked`

Valid tiers for ranked/competitive are: `comp`, `competitive`, `ranked`

All commands default to getting competitive stats and fall back to quickplay stats if the person hasn't played competitive.

If the user you're getting stats for is in the db, their stats will be in whatever tier they chose when they set their battletag.

---

* [Overwatch](#overwatchow)
* [- Heroes](#heroes)
* [- Set](#set)
* [-- tag](#tag)
* [-- mode](#mode)
* [-- region](#region)
* [- Unset](#unset)

---

## Overwatch/OW
#### Get your own or another user's stats.
This command can be used with `!ow` or `!overwatch`
Arguments can be given in any order.

Usage:

    !ow [BattleTag/mention] [mode] [region]

    If you're added to the DB:
        !ow                        : Get your own stats in your saved tier
        !ow qp/comp                : Get your own stats and force tier

    If OtherUser is added to the DB:
        !ow @OtherUser             : Get OtherUser's stats in their saved tier
        !ow @OtherUser qp/comp     : Get OtherUser's stats and force tier

    If person is not in DB/same discord server:
        !ow BattleTag#1234         : Get BattleTag#1234's competitive stats
        !ow Battletag#1234 qp/comp : Get BattleTag#1234's stats and force tier

### Heroes
#### Get your own or another user's playtime with each hero.
Arguments can be given in any order.
Usage:

    !ow heroes [BattleTag/Mention] [mode] [region]

    If you're added to the DB:
        !ow heroes                        : Get your own hero time in your saved tier
        !ow heroes qp/comp                : Get your own stats and force tier

    If OtherUser is added to the DB:
        !ow heroes @OtherUser             : Get OtherUser's hero time in their saved tier
        !ow heroes @OtherUser qp/comp     : Get OtherUser's hero time and force tier

    If person is not in DB/same discord server:
        !ow heroes BattleTag#1234         : Get BattleTag#1234's competitive hero time
        !ow heroes Battletag#1234 qp/comp : Get BattleTag#1234's hero time and force tier

### Set
#### Add your BattleTag, preferred gamemode, and region to the DB.
Aliases: `save`
Usage:

    !ow set <BattleTag/Mention> [mode] [region]
    !ow set MyTag#1234 qp eu

#### Tag
##### Change your BattleTag in the DB.
Aliases: `btag`, `battletag`
Usage:

    !ow set tag <new tag>
    !ow set tag NewBattleTag#1234

#### Mode
##### Change your preferred mode in the DB.
Usage:

    !ow set mode <new mode>
    !ow set mode qp

#### Region
##### Change your preferred region in the DB.
Accepted regions: `us`, `kr`, `eu`
Usage:

    !ow set region <new region>
    !ow set region kr

### Unset
#### Remove your BattleTag from the DB.
Aliases: `delete`, `remove`
Usage:

    !ow unset
