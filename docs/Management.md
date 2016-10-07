# Server Management / Administration Commands
---

* [Kick](#kick)
* [Ban](#ban)
* [Join](#join)
* [Leave](#leave)
* [Purge](#purge)

---

### Kick
#### Kicks another member from the server.
##### Requires __you and the bot__ have the `Kick Members` permission.
Usage:

    !kick <mention>
    !kick @OtherUser

---
### Ban
#### Bans another member from the server.
##### Requires __you and the bot__ have the `Ban Members` permission.
Usage:

    !ban <mention>
    !ban @OtherUser

---

### Join
#### Gives you a link to invite the bot to any server you created or have the `Manage Server` permission on.
Usage:

    !join

---

### Leave
#### Makes the bot leave the server.
##### Requires __you__ have the `Kick Members` permission.
Usage:

    !leave

---

### Purge
#### Removes a certain number messages by yourself or another user.
##### Requires __the bot__ has the `Manage Messages` permission.
##### Requires __you__ have the `Manage Messages` permission if you want to purge _another user's_ messages.
Usage:

    !purge <count> [mention]
    !purge #                 : Remove # of your own messages
    !purge # @OtherUser      : Remove # of OtherUser's messages
