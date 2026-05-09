# Tracking Ablation Benchmark

Script:

```text
benchmark_tracking_ablation.py
```

Editable config:

```text
config.py
```

This benchmark measures temporal identity consistency on a custom tracking video. It compares available trackers such as ByteTrack and DeepSORT using MOT metrics:

- MOTA
- MOTP
- IDF1
- ID switches
- Mostly Tracked
- Mostly Lost
- Fragmentations
- precision
- recall

## Data

Required:

- custom tracking video
- MOTChallenge-style ground truth file

Ground-truth format:

```csv
frame,id,x,y,w,h,conf,class,visibility
1,1,120,80,90,210,1,1,1
```

## Example

```bash
python benchmark_tracking_ablation.py --video tracking_video.mp4 --ground-truth ground_truth.txt --output output --trackers bytetrack,deepsort
```

You can also edit `config.py` and run:

```bash
python benchmark_tracking_ablation.py
```

## Outputs

- `benchmark_tracking_ablation_report.json`
- `benchmark_tracking_ablation_summary.csv`
- `tracking_metrics_per_tracker.csv`
- generated tracker prediction CSV files for trackers that run successfully

