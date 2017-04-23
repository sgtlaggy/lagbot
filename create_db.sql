CREATE DATABASE lagbot;
\c lagbot
CREATE TABLE overwatch (
    id text PRIMARY KEY,
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
    owner_id text,
    modified_at timestamp DEFAULT (now() at time zone 'utc')
);
CREATE TABLE tagusers (
    id text PRIMARY KEY,
    uses integer DEFAULT 1
);
CREATE TABLE noshorttag (
    guild_id text PRIMARY KEY
);
CREATE TABLE prefixes (
    guild_id text PRIMARY KEY,
    prefix text,
    allow_default boolean
);
CREATE TABLE reminders (
    message_id text PRIMARY KEY,
    channel_id text,
    author_id text,
    content text,
    end_at timestamp
);
CREATE TABLE polls (
    message_id text PRIMARY KEY,
    channel_id text,
    author_id text,
    title text,
    options text[],
    end_at timestamp,
    cancelled boolean DEFAULT FALSE
);
