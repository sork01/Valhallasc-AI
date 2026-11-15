// A route that starts with a hairpin: from (276, 226) the Visit Alderhaven walk turns a hard 90 degrees at (259, 233), and the follower
// used to hold the next waypoint back until the hero stood on the corner, so the server stood still there for the trip to the client and back
// (two snapshots, 79% in the slowest second). The last .15 s of a leg now goes out even when the straight line to the next leg is blocked.
// Same checks as walk-route-ui, from the corner start. Mutation: remove `||Math.hypot(...)<m.v*.15` from the route follower's while loop in field.js and the lead check fails (0.00-0.20 tiles).
process.env.START = process.env.START || '276,226';
require('./walk-route-ui.cjs');
