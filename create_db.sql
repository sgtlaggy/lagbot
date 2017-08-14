CREATE DATABASE lagbot;
\c lagbot
CREATE TABLE overwatch (
    id bigint PRIMARY KEY,
    btag text,
    mode text,
    region text
);
CREATE TABLE xkcd (
    num integer PRIMARY KEY,
    safe_title text,
    alt text,
    img text,
    date date
);
CREATE TABLE prefixes (
    guild_id bigint PRIMARY KEY,
    prefix text,
    allow_default boolean
);
CREATE TABLE newrole (
    guild_id bigint PRIMARY KEY,
    role_id bigint
);
