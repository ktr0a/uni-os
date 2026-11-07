// iCal reader against hand-made feeds shaped like Google's export. `npm test`
import assert from "node:assert/strict";
import { occurrences, unescapeText } from "../src/ical";
import { dayKey, hm, zdate } from "../src/model";
import { check, finish, useFixtureRegistry } from "./helpers";

// The reader's zone is the term's (Europe/Zurich in the fixture config).
useFixtureRegistry();

const cal = (body: string) =>
  [
    "BEGIN:VCALENDAR",
    "PRODID:-//Google Inc//Google Calendar 70.9054//EN",
    "VERSION:2.0",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Courses",
    "X-WR-TIMEZONE:Europe/Zurich",
    "BEGIN:VTIMEZONE",
    "TZID:Europe/Zurich",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:+0200",
    "TZOFFSETTO:+0100",
    "DTSTART:19701025T030000",
    "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
    body.trim(),
    "END:VCALENDAR",
    "",
  ].join("\r\n");

const from = zdate(2026, 10, 19, 0, 0);
const to = zdate(2026, 11, 9, 0, 0);

const lecture = cal(`
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20260916T101500
DTEND;TZID=Europe/Zurich:20260916T120000
RRULE:FREQ=WEEKLY;WKST=MO;UNTIL=20261218T225959Z;BYDAY=WE,FR
EXDATE;TZID=Europe/Zurich:20261023T101500
DTSTAMP:20261027T064500Z
UID:lecture-la-series@example.invalid
LOCATION:Main building 101
SUMMARY:V: LA
DESCRIPTION:Linear Algebra – lecture\\, Wed + Fri 10:15–12:00\\nMain building 101 (live str
 eam into room 102).
STATUS:CONFIRMED
BEGIN:VALARM
ACTION:DISPLAY
TRIGGER:-P0DT0H30M0S
END:VALARM
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261104T110000
DTEND;TZID=Europe/Zurich:20261104T124500
DTSTAMP:20261027T064500Z
UID:lecture-la-series@example.invalid
RECURRENCE-ID;TZID=Europe/Zurich:20261104T101500
SUMMARY:V: LA (moved)
LOCATION:Room 205
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261030T101500
DTEND;TZID=Europe/Zurich:20261030T120000
DTSTAMP:20261027T064500Z
UID:lecture-la-series@example.invalid
RECURRENCE-ID;TZID=Europe/Zurich:20261030T101500
SUMMARY:V: LA
STATUS:CANCELLED
END:VEVENT
`);

check("weekly series across the DST change keeps its wall-clock time", () => {
  const occ = occurrences(lecture, from, to);
  const wed21 = occ.find((o) => dayKey(o.start) === "2026-10-21")!;
  const wed28 = occ.find((o) => dayKey(o.start) === "2026-10-28")!;
  assert.equal(hm(wed21.start), "10:15");
  assert.equal(hm(wed28.start), "10:15");
  assert.equal(wed21.start.toISOString(), "2026-10-21T08:15:00.000Z"); // CEST
  assert.equal(wed28.start.toISOString(), "2026-10-28T09:15:00.000Z"); // CET
  assert.equal(hm(wed28.end), "12:00");
});
check("EXDATE removes Fri 23 Oct, cancelled override removes Fri 30 Oct", () => {
  const days = occurrences(lecture, from, to).map((o) => dayKey(o.start));
  assert.deepEqual(days, ["2026-10-21", "2026-10-28", "2026-11-04", "2026-11-06"]);
});
check("moved instance replaces the original slot", () => {
  const moved = occurrences(lecture, from, to).find((o) => dayKey(o.start) === "2026-11-04")!;
  assert.equal(moved.title, "V: LA (moved)");
  assert.equal(hm(moved.start), "11:00");
  assert.equal(moved.location, "Room 205");
});
check("folded and escaped text; VALARM ignored", () => {
  const o = occurrences(lecture, from, to)[0];
  assert.equal(o.desc, "Linear Algebra – lecture, Wed + Fri 10:15–12:00\nMain building 101 (live stream into room 102).");
  assert.equal(unescapeText("a\\;b\\\\c"), "a;b\\c");
});

const misc = cal(`
BEGIN:VEVENT
DTSTART:20261028T091500Z
DTEND:20261028T110000Z
UID:once@example.invalid
SUMMARY:E: PROG
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261101
DTEND;VALUE=DATE:20261102
UID:allday@example.invalid
SUMMARY:Public holiday
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Vienna:20261026T111500
DURATION:PT45M
RRULE:FREQ=DAILY;COUNT=3
UID:daily@example.invalid
SUMMARY:[DM]
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20260907T180000
DTEND;TZID=Europe/Zurich:20260907T190000
RRULE:FREQ=MONTHLY;BYDAY=1MO
UID:monthly@example.invalid
SUMMARY:Monthly review
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261027T090000
DTEND;TZID=Europe/Zurich:20261027T100000
RRULE:FREQ=WEEKLY
UID:gone@example.invalid
SUMMARY:Cancelled series
STATUS:CANCELLED
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261026T120000
DTEND;TZID=Europe/Zurich:20261026T130000
RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO
UID:biweekly@example.invalid
SUMMARY:AD recall
END:VEVENT
`);

check("UTC one-off", () => {
  const o = occurrences(misc, from, to).find((x) => x.uid === "once@example.invalid")!;
  assert.equal(hm(o.start), "10:15");
  assert.equal(hm(o.end), "12:00");
});
check("all-day event", () => {
  const o = occurrences(misc, from, to).find((x) => x.uid === "allday@example.invalid")!;
  assert.ok(o.allDay);
  assert.equal(dayKey(o.start), "2026-11-01");
  assert.equal(o.end.getTime() - o.start.getTime(), 86400000);
});
check("DAILY with COUNT and DURATION, Vienna time zone", () => {
  const occ = occurrences(misc, from, to).filter((x) => x.uid === "daily@example.invalid");
  assert.deepEqual(occ.map((o) => `${dayKey(o.start)} ${hm(o.start)}-${hm(o.end)}`), ["2026-10-26 11:15-12:00", "2026-10-27 11:15-12:00", "2026-10-28 11:15-12:00"]);
});
check("MONTHLY first Monday", () => {
  const occ = occurrences(misc, from, to).filter((x) => x.uid === "monthly@example.invalid");
  assert.deepEqual(occ.map((o) => dayKey(o.start)), ["2026-11-02"]);
});
check("cancelled series is dropped; INTERVAL=2 weekly", () => {
  const occ = occurrences(misc, from, to);
  assert.ok(!occ.some((o) => o.uid === "gone@example.invalid"));
  assert.deepEqual(occ.filter((o) => o.uid === "biweekly@example.invalid").map((o) => dayKey(o.start)), ["2026-10-26", "2026-11-09"].filter((d) => d < "2026-11-09"));
});
check("RDATE adds instances (a timed bonus task on 3 Nov and 8 Dec)", () => {
  const feed = cal(`
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261103T131500
DTEND;TZID=Europe/Zurich:20261103T150000
RDATE;TZID=Europe/Zurich:20261208T131500
UID:timed
SUMMARY:PROG timed bonus task
END:VEVENT
`);
  const occ = occurrences(feed, from, zdate(2026, 12, 31));
  assert.deepEqual(occ.map((o) => `${dayKey(o.start)} ${hm(o.start)}-${hm(o.end)}`), ["2026-11-03 13:15-15:00", "2026-12-08 13:15-15:00"]);
});
check("window edges: an event ending exactly at `from` is out, one starting at `to` is out", () => {
  const edge = cal(`
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261018T230000
DTEND;TZID=Europe/Zurich:20261019T000000
UID:a
SUMMARY:ends at from
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Europe/Zurich:20261109T000000
DTEND;TZID=Europe/Zurich:20261109T010000
UID:b
SUMMARY:starts at to
END:VEVENT
`);
  assert.equal(occurrences(edge, from, to).length, 0);
});

finish();
