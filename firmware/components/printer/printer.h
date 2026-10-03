#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define PR_LINE_MAX 512
#define PR_RECENT_COUNT 128
#define PR_CARD_MAX 64
#define PR_EVENT_COUNT 32
#define PR_EVENT_TEXT_MAX 192
#define PR_PROFILE "est3_printer_observations_v2"

typedef enum { PR_UNKNOWN, PR_METADATA, PR_BOUNDARY, PR_FRAGMENT, PR_GAP, PR_EVENT } pr_kind;
typedef enum { PR_LOCAL_TROUBLE=1, PR_COMMON_TROUBLE=2 } pr_event_type;
typedef enum { PR_UNMAPPED, PR_MAPPED, PR_UNMATCHED, PR_IGNORED } pr_event_result;
typedef struct {
    uint64_t id, offset, received_ms, source_order;
    uint32_t epoch;
    unsigned panel, card, device;
    pr_event_type type;
    bool active;
    char source_time[20], text[PR_EVENT_TEXT_MAX+1];
    pr_event_result result;
} pr_event;
/* A complete printer record is an observation, never a current-state snapshot. */
typedef pr_event_result (*pr_event_sink)(void *context, const pr_event *event);
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
    pr_event events[PR_EVENT_COUNT], pending_event;
    size_t event_head, event_count;
    uint64_t events_complete, events_incomplete, events_mapped, events_unmatched, events_ignored;
    unsigned event_stage;
    bool event_boundary, event_report;
    pr_event_sink event_sink;
    void *event_context;
} pr_parser;

void pr_init(pr_parser *p);
void pr_gap(pr_parser *p, uint32_t epoch, uint64_t offset, uint64_t now, const char *reason);
void pr_feed(pr_parser *p, uint32_t epoch, uint64_t offset, uint64_t now,
             const uint8_t *data, size_t length, bool corrupt);
const pr_line *pr_recent(const pr_parser *p, size_t chronological_index);
const char *pr_kind_name(pr_kind kind);
const pr_event *pr_recent_event(const pr_parser *p, size_t chronological_index);
const char *pr_event_type_name(pr_event_type type);
const char *pr_event_result_name(pr_event_result result);
/* Internal line parser; shared by firmware and disconnected native tests. */
pr_kind pr_event_line(pr_parser *p, const char *text);
void pr_event_reset(pr_parser *p);
