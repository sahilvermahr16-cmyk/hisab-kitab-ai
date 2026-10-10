# Hisab-Kitab AI — Testing

Har command project ke **main folder** se chalao.

## Ek baar ki setup
1. Postgres mein alag test database banao (asli DB ko test kabhi nahi chhoota):
   ```
   psql -U postgres -c "CREATE DATABASE hisab_test;"
   ```
2. `.env` mein ye line jodo (password apna):
   ```
   TEST_DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/hisab_test
   ```
3. Check: `python test/reset_test_db.py` → "yes" → "✅ Test DB reset + seed ho gaya."

## Test chalana
```
python test/HK_Testing.py --bundle emp                     # Employee ke saare 50 (Hinglish)
python test/HK_Testing.py --bundle emp --only EMP-A-01     # sirf ek
python test/HK_Testing.py --bundle emp --category A,B      # sirf kuch category
```

## Folder
| Path | Kya hai |
|---|---|
| `HK_Testing.py` | Runner — har statement se pehle DB reset, statement chalata hai, beech ke sawaalon ke jawaab deta hai, sab save karta hai |
| `reset_test_db.py` | Test DB saaf karke seed daalta hai (sirf "test" naam wale DB pe) |
| `seed_data.py` | Test shuru hone se pehle DB mein kaun-kaun hoga |
| `testcases/<bundle>_testcases.py` | Statements + expected jawaab (LOCKED) |
| `results/<bundle>/*.log` | Poora terminal output — galti samajhne ke liye |
| `results/<bundle>/*.json` | Har test ka saaf saar — Excel isi se banta hai |
| `report/` | Excel test set / testing report |
