# Iteration convergence check (cornering simulations)

`iteration_check.py` produces Figure 1 and the numbers in Section 5.3 of the report.

For each Star-CCM+ monitor CSV in a folder, it finds the earliest iteration after which the
rolling 300-iteration mean of **full-car downforce** and **full-car drag** stays within ±1% of the
value reported from that run (the mean of its last 300 iterations). It also reports how far the
averaged values at iteration 2000 are from the final values.

## Usage

```bash
pip install pandas numpy matplotlib
python iteration_check.py path/to/cornering_csvs --fig ../../assets/report-figure-iteration-convergence.png
```

Options: `--tol` (percent, default 1.0), `--window` (default 300), `--limit` (default 2000),
`--original` (default 3500), `--fig` (output figure path).

Each CSV is a Star-CCM+ monitor export: the first column is the iteration number, and the
full-car totals are found by name (`DF TTL` / `DF FULL TTL` and `Drag TTL` / `DRAG FULL TTL`).
CSVs whose first column is not numeric are skipped.

## Data used in the report

The 10 cornering runs below (about 3–6 MB each, not stored in this repo). Their results are in
`iteration_check_results.csv`, where `label` matches the run names in Figure 1.

- 27_Cornering_1.0
- 27_Cornering_Package_1
- 27_FW_base_1_cut_ep_strake_flat_ep_upper_inner_2_mod_sd_2.23
- 27_FW_base_1_cut_ep_strake_flat_ep_upper_inner_2_mod_sd_2.30
- 27_FW_main_aft_mod_cut_ep_strake_flat_ep_upper_cornering
- FX63137_90T_new_ep_cut_slot_1.4_side_diff_v2.2_corner
- Main3deg2nd240mm41deg3rd64deg110mm1650mmslot
- Main3deg2nd240mm41deg3rd64deg110mm1850mmslot7mmGurney
- Main3deg2nd240mm43deg3rd66deg110mm1850mmslot
- Main3deg2nd240mm43deg3rd68deg110mm1650mmslot
