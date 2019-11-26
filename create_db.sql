CREATE ROLE lagbot WITH LOGIN PASSWORD 'password';
CREATE DATABASE lagbot WITH OWNER lagbot;

\c lagbot lagbot

CREATE TABLE overwatch (
    id bigint PRIMARY KEY,
    btag text,
    mode text,
    region text
);
