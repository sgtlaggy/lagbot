# Tag Commands

---

* [Tag][#tag]
* [- Create][#create]
* [- Edit][#edit]
* [- Remove][#remove]
* [- Info][#info]
* [- Stats][#stats]
* [- List][#list]
* [- Leaderboard][#leaderboard]

---

## Tag
#### Get a tag.
This command can be called with `%` instead of `!tag`

Usage:

    !tag <name>
    %<name>

    !tag abc
    %abc

### Create
#### Create a new tag.
Usage:

    !tag create abc tag content goes here : create tag with name "abc" and content "tag content goes here"
    !tag create "a b c" tag content here  : create tag with name "a b c" and content "tag content here"
                                          : this would be called with "!tag a b c" or "%a b c"

### Edit
#### Edit a tag you created.
Usage:

    !tag edit abc new content here     : edit your tag "abc" and set content to "new content here"
    !tag edit "a b c" new content here : edit your tag "a b c" and set content to "new content here"

### Remove
#### Remove a tag you created.
Usage:

    !tag remove abc   : remove your tag "abc"
    !tag remove a b c : remove your tag "a b c"

### Info
#### Get info about a tag or the tag DB.
Usage:

    !tag info abc   : get info about tag "abc"
    !tag info a b c : get info about tag "a b c"
    !tag            : get info about the tag DB

### Stats
#### Get stats about tag usage.
Usage:

    !tag stats              : get your own tag usage
    !tag stats @OtherPerson : get OtherPerson's tag usage

### List
#### Get tags you or someone else created.
Usage:

    !tag list              : get your own created tags
    !tag list @OtherPerson : get OtherPerson's created tags

### Leaderboard
#### See a leaderboard of most used tags and users that use the most tags.
Usage:

    !tag leaderboard
