/** A part that has been ordered. It is only a claim by its source until it is received. */
export interface PartRequest extends WayBack {
  state: 'requested' | 'confirmed' | 'received'; source_id: string; source_name: string; arrives_min: number
  /** Someone should chase this: the source has not answered in time, or the part should be here and is not. */
  chase: 'no_answer' | 'not_here' | null
}

/** When the part is needed, which other source could step in, and until when without changing the plan. */
export interface WayBack {
  /** When the job is due to start or resume. A part that arrives by then changes nothing. */
  needed_by_min: number
  /** The last moment to order the backup and still have it by then. Null: there was no such moment. */
  switch_by_min: number | null
  backup_name: string | null; backup_eta_min: number | null
}

export interface PartNeed {
  part_id: string; name: string; qty: number; on_hand_home: number; sourced_from: string | null; arrives_min: number | null
  request: PartRequest | null
  /** Why this job will not get the part from the shelf, if it will not. */
  shortfall: 'out_of_stock' | 'claimed_by_earlier_jobs' | null
}

export type OrderStatus = 'done' | 'in_progress' | 'scheduled' | 'waiting_for_part' | 'unplanned'

export interface Order {
  id: string; vehicle: string; description: string; minutes: number; skill: string
  release_min: number; promise_min: number; parts: PartNeed[]
  start_min: number | null; end_min: number | null; technician: string | null; bay: string | null
  /** Technician minutes to make the car movable part-way through the job. Null: it cannot be moved while apart. */
  roll_out_min: number | null; set_up_min: number
  status: OrderStatus; late: boolean; short_of_parts: boolean
}

/** Extra pieces of a stalled job: work done before the stall, and the time its bay is blocked. */
export interface Segment { ro_id: string; kind: 'done' | 'hold'; start_min: number; end_min: number; technician: string | null; bay: string }

export interface Day {
  store: { id: string; name: string }
  sister_stores: { id: string; name: string; shuttle_minutes: number }[]
  now_min: number; day_start_clock: string; horizon_min: number; plan_version: number
  technicians: { id: string; name: string; skills: string[] }[]
  bays: { id: string; name: string; kind: string }[]
  orders: Order[]
  segments: Segment[]
  open_proposal_id: number | null
  summary: { orders: number; done: number; in_progress: number; waiting_for_part: number; scheduled: number; promises_at_risk: number; requests_to_chase: number; last_finish_min: number }
}

export interface Slot { start_min: number; end_min: number; technician: string; bay: string }

export interface SourceOption {
  id: string; name: string; kind: string; eta_min: number; cost: number
  on_hand: number | null; available: boolean; risk: number | null; risk_basis: string | null; safe: boolean
  /** What the day would look like if this source were used: a real re-plan, not an estimate. */
  outcome: SourceOutcome | null
  /** Why the engine did not choose this source. Null for the engine's own pick. */
  why_not: string | null
}

export interface SourceOutcome {
  missed_promises: number; late_minutes: number; jobs_moved: number; bay_blocked_min: number
  cost: number; arrives_min: number; proven_best: boolean; late_margin_min: number; late_margin_capped: boolean
}

export interface PlanOption extends WayBack {
  key: string; title: string; source_id: string; source_name: string; arrives_min: number; cost: number
  missed_promises: number; late_minutes: number; jobs_moved: number; bay_blocked_min: number
  proven_best: boolean; solve_seconds: number; stalled_job: Slot
  /** How late the part can be before another promise is lost, in 15-minute steps up to 4 hours. */
  late_margin_min: number; late_margin_capped: boolean
  /** Why this plan must be approved by a person. Empty when nothing is traded off. */
  needs_you: string[]
  /** What happens to a car already on the lift: it waits in its bay, or it is rolled out. Null if work had not started. */
  bay_decision: 'hold' | 'roll_out' | null; bay_note: string | null; rolled_out_until: number | null
  changes: { ro_id: string; description: string; before: Slot; after: Slot }[]
  late_orders: { ro_id: string; vehicle: string; description: string; promise_min: number; end_min: number; late_before: boolean }[]
  assignments: Record<string, Slot>
}

export interface Proposal {
  id: number; status: string; plan_version: number
  /** A part that is missing, or a part already on its way that will arrive at a new time. */
  kind: 'missing_part' | 'late_part'; old_arrives_min?: number; new_arrives_min?: number | null
  /** For a part on its way: why its source is being planned again, and which source it was. */
  why?: 'new_time' | 'cannot_supply' | 'no_answer'; old_source_id?: string; old_source_name?: string
  ro_id: string; vehicle: string; description: string; promise_min: number
  part_id: string; part_name: string; qty: number; now_min: number; in_progress: boolean
  forced_source: string | null; forced_bay: 'hold' | 'roll_out' | null; can_roll_out: boolean; engine_source_id: string; current: Slot; sources: SourceOption[]; options: PlanOption[]
  no_replan: { source_id: string; source_name: string; arrives_min: number; missed_promises: number; late_minutes: number; bay_blocked_min: number }
}

export interface LogEntry {
  id: number; at_min: number; kind: string
  detail: Record<string, unknown> & { customer_messages?: { ro_id: string; text: string }[] }
}

export interface PrecheckItem {
  ro_id: string; vehicle: string; description: string; start_min: number; promise_min: number
  part_id: string; part_name: string; qty: number; reason: 'out_of_stock' | 'claimed_by_earlier_jobs'; already_started: boolean
  /** A safe source that can deliver before the job starts, if there is one. */
  fix: { source_id: string; source_name: string; arrives_min: number; cost: number } | null
}

export interface Precheck {
  checked_at_min: number; jobs_checked: number; flagged: PrecheckItem[]
  fixable_without_replan: number; need_a_decision: number; fix_cost: number
}

/** What a note was read as: a technician's report, or a source's reply about an ordered part. Nothing happens until a person confirms it. */
export interface NoteReading {
  kind: 'missing_part' | 'late_part' | 'confirmed' | 'received' | 'cannot_supply' | 'unclear'
  ro_id: string | null; part_id: string | null; arrives_min: number | null
  vehicle: string | null; description: string | null; part_name: string | null
  /** Where the part was ordered from; null for a missing part. */
  source_name: string | null
  /** The exact words of the note the reading rests on. */
  quote: string | null; why_unclear: string | null
  /** 'rules', or 'model: <name>'. */
  read_by: string
  /** Set when a model was set up but its answer could not be used. */
  fell_back_because: string | null
}

export interface ReaderScore { dev: { right: number; of: number }; held_out: { right: number; of: number }; outside: { right: number; of: number } }

export interface IntakeInfo { reader: string; sends_notes_out: boolean; eval: Record<string, ReaderScore> | null }

export type LateCheck =
  | { holds: true; starts_min: number; spare_min: number; arrives_min: number }
  | { holds: false; arrives_min: number; missed_promises: number; late_minutes: number; jobs_moved: number }
