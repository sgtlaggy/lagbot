# Overwatch Stat Commands

#### Note these commands may not give 100% accurate information due to [OWAPI](https://github.com/SunDwarf/OWAPI) being down or Blizzard changing how they format data or being a bit behind on real stats.

Valid tiers for unranked/quickplay are: `quick`, `quickplay`, `qp`, `general`, `unranked`

Valid tiers for ranked/competitive are: `comp`, `competitive`, `ranked`

All commands default to getting competitive stats and fall back to quickplay stats if the person hasn't played competitive.

If the user you're getting stats for is in the db, their stats will be in whatever tier they chose when they set their battletag.

---

* [Overwatch](#overwatchow)
* [Heroes](#heroes)
* [Set](#set)
* [Unset](#unset)

---

## Overwatch/OW
#### Get your own or another user's stats.
This command can be used with `!ow` or `!overwatch`

Usage:

    !ow [BattleTag/mention] [tier]

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
Usage:

    !ow heroes [BattleTag/Mention] [tier]

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
#### Add your BattleTag and whether you prefer quickplay or competitive stats be shown for yourself to the DB.
Usage:

    !ow set [BattleTag/Mention] [tier]

    If you're added to the DB:
        !ow set BattleTag#1234         : Change your BattleTag in the DB
        !ow set qp/comp                : Change the tier your have saved in the DB

    If person is not in DB/same discord server:
        !ow set BattleTag#1234         : Set your BattleTag in the DB
        !ow set Battletag#1234 qp/comp : Set your BattleTag and preferred tier

### Unset
#### Remove your BattleTag from the DB.
Usage:

    !ow unset
