# Wiki source

These are the source pages for the project's [GitHub Wiki](../../wiki). They live
in the repo so they're version-controlled alongside the code (GitHub wikis are a
separate git repo and easy to lose track of).

## Publishing

GitHub creates the wiki's git repo only **after the first page exists**, and
there's no API to create it. So the first time:

1. Open `https://github.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/wiki`
   and click **Create the first page** → type anything → **Save**.
2. From the repo root, run the publish script:

   ```bash
   ./wiki/publish.sh
   ```

After that, re-running `./wiki/publish.sh` syncs any edits you make here up to the
live wiki. `Home.md` is the landing page; page links use `[[Page Name]]` syntax.
