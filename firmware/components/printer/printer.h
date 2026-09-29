#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PR_LINE_MAX 512
#define PR_RECENT_COUNT 128
#define PR_CARD_MAX 64

typedef enum { PR_UNKNOWN, PR_METADATA, PR_BOUNDARY, PR_FRAGMENT, PR_GAP } pr_kind;
typedef struct {
    uint64_t id, offset, received_ms;
    uint32_t epoch;
    pr_kind kind;
    size_t length;
    uint8_t raw[PR_LINE_MAX];
} pr_line;
typedef struct {
    unsigned address;
    char ann_type[32], type[32], firmware[24], bootstrap[24], database[24];
    char firmware_date[16], bootstrap_date[16], database_date[16];
} pr_card;
typedef struct {
    bool active, complete, tainted, panel_seen;
    unsigned panel, historical_alarm_count;
    uint64_t received_ms;
    uint32_t epoch;
    char source_time[32], cpu[24], sdu[24], project[24], database_serial[32];
    char database_date[16], market[32], ip[32], netmask[32], gateway[32];
    size_t card_count;
    pr_card cards[PR_CARD_MAX];
} pr_report;
typedef struct {
    pr_line recent[PR_RECENT_COUNT];
    size_t head, count, partial_length;
    uint8_t partial[PR_LINE_MAX];
    uint64_t next_id, evicted, gaps, unknown, fragments, reports_complete, reports_incomplete;
    uint64_t next_offset, line_offset, received_ms;
    uint32_t epoch;
    bool initialized, skip_lf, fragmenting;
    int date_target;
    pr_report report, last_complete;
} pr_parser;

void pr_init(pr_parser *p);
void pr_gap(pr_parser *p, uint32_t epoch, uint64_t offset, uint64_t now, const char *reason);
void pr_feed(pr_parser *p, uint32_t epoch, uint64_t offset, uint64_t now,
             const uint8_t *data, size_t length, bool corrupt);
const pr_line *pr_recent(const pr_parser *p, size_t chronological_index);
const char *pr_kind_name(pr_kind kind);
