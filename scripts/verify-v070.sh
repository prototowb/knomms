#!/usr/bin/env bash
# Live verification for v0.7.0 — teams, ACL grants, org explore (docs/10-teams-and-acls.md §9).
# Three users: A = dev@localhost.dev (Default org admin), B = test@example.com (same org),
# C = freshly registered org-less user. Run with the stack up and migration 014 applied.
set -u
API="http://localhost/api/v1"
PASS=0; FAIL=0

say()  { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
ok()   { PASS=$((PASS+1)); printf '  ✓ %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  ✗ %s\n' "$*"; }
check() { # check <desc> <expected_status> <actual_status>
  if [ "$2" = "$3" ]; then ok "$1 [$3]"; else bad "$1 — expected $2, got $3"; fi
}

jqr() { python3 -c "import sys,json;d=json.load(sys.stdin);print(eval(sys.argv[1]))" "$1" 2>/dev/null; }

login() { curl -s -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$1\",\"password\":\"$2\"}" | jqr "d['access_token']"; }

say "Login A + B, register C (org-less)"
TA=$(login dev@localhost.dev devdev99)
TB=$(login test@example.com password123)
C_EMAIL="carol-$(date +%s)@example.com"
curl -s -X POST "$API/auth/register" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$C_EMAIL\",\"handle\":\"carol$(date +%s)\",\"display_name\":\"Carol\",\"password\":\"password123\"}" >/dev/null
TC=$(login "$C_EMAIL" password123)
[ -n "$TA" ] && [ -n "$TB" ] && [ -n "$TC" ] && ok "three tokens issued" || bad "token issuance"

AH="Authorization: Bearer $TA"; BH="Authorization: Bearer $TB"; CH="Authorization: Bearer $TC"
B_ID=$(curl -s "$API/auth/me" -H "$BH" | jqr "d['id']")
C_ID=$(curl -s "$API/auth/me" -H "$CH" | jqr "d['id']")
ORG_NAME=$(curl -s "$API/auth/me" -H "$AH" | jqr "d['org_name']")
[ "$ORG_NAME" = "Default organisation" ] && ok "UserOut.org_name resolved ('$ORG_NAME')" || bad "org_name missing (got '$ORG_NAME')"

say "1. Teams — create, same-org guard, manage guard"
TEAM_NAME="Verifiers-$(date +%s)"
TEAM=$(curl -s -X POST "$API/orgs/teams" -H "$AH" -H 'Content-Type: application/json' -d "{\"name\":\"$TEAM_NAME\"}")
TEAM_ID=$(echo "$TEAM" | jqr "d['id']")
[ -n "$TEAM_ID" ] && ok "A created team $TEAM_ID (auto-member: $(echo "$TEAM" | jqr "len(d['members'])"))" || bad "team create: $TEAM"
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/orgs/teams/$TEAM_ID/members" -H "$AH" -H 'Content-Type: application/json' -d "{\"user_id\":\"$B_ID\"}")
check "A adds B to team" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/orgs/teams/$TEAM_ID/members" -H "$AH" -H 'Content-Type: application/json' -d "{\"user_id\":\"$C_ID\"}")
check "adding org-less C refused" 409 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/orgs/teams" -H "$AH" -H 'Content-Type: application/json' -d "{\"name\":\"$TEAM_NAME\"}")
check "duplicate team name refused" 409 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$API/orgs/teams/$TEAM_ID/members/$B_ID" -H "$CH")
check "org-less C cannot touch the team" 404 "$S"

say "2. Team viewer grant on a PRIVATE KB → B reads, C 404"
KB=$(curl -s -X POST "$API/kbs" -H "$AH" -H 'Content-Type: application/json' -d '{"title":"ACL verify KB","visibility":"private"}')
KB_ID=$(echo "$KB" | jqr "d['id']")
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH");  check "pre-grant: B 404s private KB" 404 "$S"
GR=$(curl -s -X POST "$API/kbs/$KB_ID/grants" -H "$AH" -H 'Content-Type: application/json' \
  -d "{\"principal_type\":\"team\",\"principal\":\"$TEAM_ID\",\"permission\":\"viewer\"}")
GRANT_ID=$(echo "$GR" | jqr "d['id']")
[ -n "$GRANT_ID" ] && ok "team viewer grant created ($(echo "$GR" | jqr "d['principal_label']"))" || bad "grant create: $GR"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH");          check "B reads KB via team grant" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID/sources" -H "$BH");  check "B lists sources" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID/search?q=test" -H "$BH"); check "B searches KB" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$CH");          check "C still 404s" 404 "$S"
LIST=$(curl -s "$API/kbs" -H "$BH")
echo "$LIST" | grep -q "$KB_ID" && ok "granted KB appears in B's dashboard list" || bad "granted KB missing from B's list"
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/sources/" -H "$BH" -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"$KB_ID\",\"url\":\"https://example.com\"}")
check "viewer B cannot add sources" 404 "$S"

say "3. Direct user grant (cross-org) on a private asset → C reads"
ASSET=$(curl -s -X POST "$API/assets" -H "$AH" -H 'Content-Type: application/json' \
  -d '{"title":"ACL verify asset","description":"","asset_type":"system_prompt","visibility":"private"}')
ASSET_ID=$(echo "$ASSET" | jqr "d['id']")
C_HANDLE=$(curl -s "$API/auth/me" -H "$CH" | jqr "d['handle']")
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/assets/$ASSET_ID" -H "$CH"); check "pre-grant: C 404s asset" 404 "$S"
curl -s -X POST "$API/assets/$ASSET_ID/grants" -H "$AH" -H 'Content-Type: application/json' \
  -d "{\"principal_type\":\"user\",\"principal\":\"$C_HANDLE\",\"permission\":\"viewer\"}" >/dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/assets/$ASSET_ID" -H "$CH"); check "C reads asset via user grant" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/assets/$ASSET_ID/grants" -H "$CH" -H 'Content-Type: application/json' \
  -d "{\"principal_type\":\"user\",\"principal\":\"$C_HANDLE\",\"permission\":\"editor\"}")
check "non-owner cannot manage grants" 403 "$S"

say "4. Editor grant → B writes (KB source, asset version, harness slot)"
curl -s -X POST "$API/kbs/$KB_ID/grants" -H "$AH" -H 'Content-Type: application/json' \
  -d "{\"principal_type\":\"team\",\"principal\":\"$TEAM_ID\",\"permission\":\"editor\"}" >/dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/sources/" -H "$BH" -H 'Content-Type: application/json' \
  -d "{\"kb_id\":\"$KB_ID\",\"url\":\"https://example.com\"}")
check "editor B adds a URL source (upsert grant→editor)" 202 "$S"
B_HANDLE=$(curl -s "$API/auth/me" -H "$BH" | jqr "d['handle']")
curl -s -X POST "$API/assets/$ASSET_ID/grants" -H "$AH" -H 'Content-Type: application/json' \
  -d "{\"principal_type\":\"user\",\"principal\":\"$B_HANDLE\",\"permission\":\"editor\"}" >/dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/assets/$ASSET_ID/versions" -H "$BH" -H 'Content-Type: application/json' \
  -d '{"content":"You are helpful. v2 by editor.","rationale":"editor commit"}')
check "editor B commits an asset version" 201 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/assets/$ASSET_ID/versions" -H "$CH" -H 'Content-Type: application/json' \
  -d '{"content":"viewer should fail","rationale":"x"}')
check "viewer C cannot commit versions" 403 "$S"
HARNESS=$(curl -s -X POST "$API/harnesses" -H "$AH" -H 'Content-Type: application/json' \
  -d '{"title":"ACL verify harness","description":"","visibility":"private"}')
HARNESS_ID=$(echo "$HARNESS" | jqr "d['id']")
AV_ID=$(curl -s "$API/assets/$ASSET_ID" -H "$AH" | jqr "d['versions'][0]['id']")
curl -s -X POST "$API/harnesses/$HARNESS_ID/grants" -H "$AH" -H 'Content-Type: application/json' \
  -d "{\"principal_type\":\"user\",\"principal\":\"$B_HANDLE\",\"permission\":\"editor\"}" >/dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/harnesses/$HARNESS_ID/assets" -H "$BH" -H 'Content-Type: application/json' \
  -d "{\"asset_version_id\":\"$AV_ID\",\"role\":\"system_prompt\"}")
check "editor B adds a harness slot" 201 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/harnesses/$HARNESS_ID/eval" -H "$BH")
check "editor B reads eval-run list" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/harnesses/$HARNESS_ID/eval" -H "$CH")
check "outsider C 404s eval-run list" 404 "$S"

say "5. Revocation & team-removal immediacy (unchanged tokens)"
GRANTS=$(curl -s "$API/kbs/$KB_ID/grants" -H "$AH")
GRANT_ID=$(echo "$GRANTS" | jqr "d[0]['id']")
curl -s -X DELETE "$API/kbs/$KB_ID/grants/$GRANT_ID" -H "$AH" -o /dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH")
check "revoke → B loses KB instantly" 404 "$S"
curl -s -X POST "$API/kbs/$KB_ID/grants" -H "$AH" -H 'Content-Type: application/json' \
  -d "{\"principal_type\":\"team\",\"principal\":\"$TEAM_ID\",\"permission\":\"viewer\"}" >/dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH"); check "re-grant → B reads again" 200 "$S"
curl -s -X DELETE "$API/orgs/teams/$TEAM_ID/members/$B_ID" -H "$AH" -o /dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH")
check "removed from team → B loses team-grant access" 404 "$S"

say "6. Org-leave cascade (B re-added, then leaves org)"
curl -s -X POST "$API/orgs/teams/$TEAM_ID/members" -H "$AH" -H 'Content-Type: application/json' -d "{\"user_id\":\"$B_ID\"}" -o /dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH"); check "back in team → B reads" 200 "$S"
INVITE=$(curl -s "$API/orgs/me" -H "$AH" | jqr "d['invite_code']")
curl -s -X POST "$API/orgs/leave" -H "$BH" -o /dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH")
check "B left org → team membership purged → KB 404" 404 "$S"
curl -s -X POST "$API/orgs/join" -H "$BH" -H 'Content-Type: application/json' -d "{\"invite_code\":\"$INVITE\"}" -o /dev/null
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/$KB_ID" -H "$BH")
check "rejoined org but NOT auto-restored to team" 404 "$S"

say "7. Org explore"
TEAM_KB=$(curl -s -X POST "$API/kbs" -H "$AH" -H 'Content-Type: application/json' -d '{"title":"Org tab KB","visibility":"team"}')
TEAM_KB_ID=$(echo "$TEAM_KB" | jqr "d['id']")
ORG_LIST=$(curl -s "$API/kbs/org" -H "$BH")
echo "$ORG_LIST" | grep -q "$TEAM_KB_ID" && ok "B sees A's team KB in /kbs/org" || bad "/kbs/org missing team KB"
echo "$ORG_LIST" | grep -q "$KB_ID" && bad "/kbs/org leaks the PRIVATE granted KB" || ok "private granted KB stays out of /kbs/org"
C_ORG=$(curl -s "$API/kbs/org" -H "$CH")
[ "$C_ORG" = "[]" ] && ok "org-less C gets empty /kbs/org" || bad "org-less C got: $C_ORG"
echo "$ORG_LIST" | grep -q "vector_namespace" && bad "/kbs/org leaks vector_namespace" || ok "PublicKBOut shape (no vector_namespace)"

say "8. Regression — public listings & logged-out"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/public"); check "public KB list, no auth" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost/api/boards?sort=trending&limit=3"); check "public boards BFF" 200 "$S"
S=$(curl -s -o /dev/null -w '%{http_code}' "$API/kbs/org"); check "/kbs/org rejects missing auth" 401 "$S"

printf '\n\033[1mRESULT: %d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
