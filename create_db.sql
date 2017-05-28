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
CREATE TABLE tags (
    name text PRIMARY KEY,
    content text,
    uses integer DEFAULT 0,
    owner_id bigint,
    modified_at timestamp DEFAULT (now() at time zone 'utc')
);
CREATE TABLE noshorttag (
    guild_id bigint PRIMARY KEY
);
CREATE TABLE prefixes (
    guild_id bigint PRIMARY KEY,
    prefix text,
    allow_default boolean
);
CREATE TABLE reminders (
    message_id bigint PRIMARY KEY,
    channel_id bigint,
    author_id bigint,
    content text,
    end_at timestamp
);
CREATE TABLE polls (
    message_id bigint PRIMARY KEY,
    channel_id bigint,
    author_id bigint,
    title text,
    options text[],
    end_at timestamp,
    cancelled boolean DEFAULT FALSE
);
