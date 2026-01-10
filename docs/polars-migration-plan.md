# Polars Migration Plan

## Current Status
- **Current Library**: pandas
- **Current Performance**: ~20 seconds for 1.4M rows
- **Bottleneck**: CSV reading + Pydantic validation

## Why Polars?

Polars is a high-performance DataFrame library written in Rust that offers:
- **5-10x faster CSV reading** than pandas
- Parallel processing by default
- More efficient memory usage
- Similar API to pandas (easy migration)

## Expected Performance Improvement

After migrating to Polars:
- **Target**: 20s → 2-4s (5-10x improvement)
- This addresses the CSV reading bottleneck
- Pydantic validation will still be a factor, but faster CSV I/O helps significantly

## Migration Steps

1. **Add Polars dependency**
   ```toml
   dependencies = [
       "polars>=0.20.0",
       # ... existing deps
   ]
   ```

2. **Update `src/scratchi/data_loader/loader.py`**
   - Replace `pd.read_csv()` with `pl.read_csv()`
   - Replace `df.itertuples()` with Polars iteration (`.iter_rows()` or `.to_dicts()`)
   - Adapt column access patterns

3. **Consider keeping pandas as optional** (if needed elsewhere)
   - Or fully migrate to Polars throughout codebase

4. **Testing**
   - Ensure all tests pass with Polars
   - Verify data integrity (all 1.4M rows parse correctly)
   - Performance benchmark comparison

## Alternative: Hybrid Approach

If full migration is too risky:
- Use Polars for CSV reading only
- Convert to pandas DataFrame: `df_polars.to_pandas()`
- Keep existing iteration logic
- Moderate improvement, lower risk

## References

- Polars docs: https://docs.pola.rs/
- Polars CSV reading: `pl.read_csv()` with various performance options
- Polars iteration: `.iter_rows()`, `.to_dicts()`, or `.to_numpy()`

## Notes

- Current code uses `itertuples()` which is already optimized
- Main bottleneck after Phase 1 optimizations: Pydantic validation
- Polars will help with CSV I/O, but Phase 2 (pre-transform data) is still valuable
- Consider combining: Polars CSV reading + pandas pre-transformation + Pydantic
