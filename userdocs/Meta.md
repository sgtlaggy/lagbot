# Meta / Bot-Related Commands
---

* [Manage](#manage)
* [Manage Nick](#nick)
* [Source](#source)
* [Info](#info)
* [Uptime](#uptime)
* [Poke](#poke)

---

## Manage
##### This is a base command that does nothing.

### Nick
#### Change the bot's nickname (not username).
##### Requires __you__ have the `Manage Nicknames` permission.
##### Requires __the bot__ has the `Change Nickname` permission.
Usage:

    !manage nick <new nickname>
    !manage nick                : Remove nickname
    !manage nick RoboCop        : Give the bot the new name "RoboCop"

---

### Source
#### Get information about the bot and its source code.
Usage:

    !source

---

### Info
#### Get information about the bot or another user.
Usage:

    !info [mention]
    !info            : Get bot's user info
    !info @OtherUser : Get OtherUser's user info

---

### Uptime
#### Get the amount of time the bot has been online.
Usage:

    !uptime

---

### Poke/Ping
#### Ping the bot to make sure it's online and working properly.
Note: The only difference in how you use the command is the phrase the bot responds with.

Usage:

    !poke
    !ping
