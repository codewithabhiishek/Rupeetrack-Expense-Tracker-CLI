"""
Student Expense Tracker
Retrod Travel Tech Hackathon — Wooble
Author: Abhishek (github.com/codewithabhiishek)
"""

import json
import os
import sys
import csv
import calendar
from typing import Optional
from datetime import datetime, date, timedelta
from collections import defaultdict

# ── Terminal colors (stdlib only, no colorama) ─────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    MAGENTA = "\033[95m"

def clr(text, *codes) -> str:
    return "".join(codes) + str(text) + C.RESET

# ── UI primitives ──────────────────────────────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def divider():
    print(clr("  " + "─" * 42, C.DIM))

def prompt(msg: str, default=None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    val = input(clr(f"  → {msg}{suffix}: ", C.YELLOW)).strip()
    return val if val else (str(default) if default is not None else "")

def success(msg): print(clr(f"  ✔  {msg}", C.GREEN, C.BOLD))
def error(msg):   print(clr(f"  ✖  {msg}", C.RED, C.BOLD))
def info(msg):    print(clr(f"  ℹ  {msg}", C.CYAN))

# ── Constants ──────────────────────────────────────────────────────────────────
DATA_FILE  = "expenses.json"
CATEGORIES = ["food", "travel", "recharge", "other"]
CAT_COLORS = {"food": C.GREEN, "travel": C.YELLOW, "recharge": C.MAGENTA, "other": C.WHITE}
RUPEE      = "₹"


# ══════════════════════════════════════════════════════════════════════════════
class ExpenseTracker:
    """Core application class — owns all state and business logic."""

    def __init__(self):
        if os.name == "nt":
            try:
                os.system("")  # Enables ANSI escape code parsing in Windows terminals
            except OSError:
                pass
        self.expenses: list  = []
        self.next_id:  int   = 1
        self.budget:   Optional[float] = None
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.expenses = data.get("expenses", [])
                self.next_id  = data.get("next_id", 1)
                self.budget   = data.get("budget")
                return
            except (json.JSONDecodeError, KeyError, OSError, AttributeError):
                # Corrupted/locked/wrong-format file — back it up and start fresh with seed data
                try:
                    os.rename(DATA_FILE, DATA_FILE + ".bak")
                except OSError:
                    pass  # can't rename either (e.g. permissions) — just move on
                info("Corrupted/invalid data file backed up. Starting fresh.")
        self._seed()
        self.save()

    def save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:  # FIX: utf-8 for ₹ symbol
                json.dump({
                    "expenses": self.expenses,
                    "next_id":  self.next_id,
                    "budget":   self.budget,
                }, f, indent=2)
        except OSError as e:
            error(f"Could not save data: {e}")

    def _seed(self):
        """Realistic sample data so reviewers see output immediately."""
        today = date.today()
        def d(offset): return (today - timedelta(days=offset)).isoformat()
        self.expenses = [
            {"id": 1, "date": d(13), "amount": 120.0,  "category": "food",     "note": "College canteen"},
            {"id": 2, "date": d(9),  "amount": 239.0,  "category": "recharge", "note": "Jio recharge"},
            {"id": 3, "date": d(6),  "amount": 349.0,  "category": "travel",   "note": "Ola ride to exam center"},
            {"id": 4, "date": d(4),  "amount": 85.0,   "category": "food",     "note": "Zomato dinner"},
            {"id": 5, "date": d(2),  "amount": 499.0,  "category": "other",    "note": "Course book"},
            {"id": 6, "date": d(1),  "amount": 60.0,   "category": "travel",   "note": "Metro card recharge"},
        ]
        self.next_id = 7
        self.budget  = 2000.0

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _total(self, expenses=None) -> float:
        target = self.expenses if expenses is None else expenses
        return sum(e["amount"] for e in target)

    def _month_expenses(self, month: Optional[str] = None) -> list:
        m = month or date.today().isoformat()[:7]
        return [e for e in self.expenses if e["date"].startswith(m)]

    def _by_category(self, expenses=None) -> dict:
        by_cat = defaultdict(float)
        target = self.expenses if expenses is None else expenses
        for e in target:
            by_cat[e["category"]] += e["amount"]
        return dict(by_cat)

    def _streak(self) -> int:
        """Consecutive days (ending today or yesterday) on which at least one expense exists."""
        recorded = {e["date"] for e in self.expenses}
        streak, day = 0, date.today()
        if day.isoformat() not in recorded:
            # If no expense today, streak can still be active if yesterday had one
            day -= timedelta(days=1)
        while day.isoformat() in recorded:
            streak += 1
            day -= timedelta(days=1)
        return streak

    def _resolve_category(self, raw: str) -> Optional[str]:
        raw = raw.lower().strip()
        if raw.isdigit():
            idx = int(raw) - 1
            return CATEGORIES[idx] if 0 <= idx < len(CATEGORIES) else None
        return raw if raw in CATEGORIES else None

    def _budget_bar(self, spent: float, budget: float):
        if budget <= 0:
            return
        actual_pct = spent / budget          # FIX: real percentage, may exceed 1.0
        bar_pct    = min(actual_pct, 1.0)   # FIX: cap only the visual bar
        fill  = max(0, int(bar_pct * 20))
        bar   = "█" * fill + "░" * (20 - fill)
        color = C.RED if actual_pct >= 1.0 else C.YELLOW if actual_pct >= 0.8 else C.GREEN
        label = "OVER BUDGET 🚨" if actual_pct >= 1.0 else "Warning ⚠️" if actual_pct >= 0.8 else "Good 👍"
        print(clr(f"  Budget   {RUPEE}{budget:.0f}", C.WHITE, C.BOLD))
        print(clr(f"  Spent    {RUPEE}{spent:.2f}  ({actual_pct*100:.1f}%)", color, C.BOLD))  # FIX: shows 150.0% not 100.0%
        print(clr(f"  [{bar}]  {label}", color))

    # ── Menu actions ──────────────────────────────────────────────────────────
    def add_expense(self):
        print(clr("\n  ── Add Expense ──", C.CYAN, C.BOLD))

        date_str = prompt("Date (YYYY-MM-DD)", default=date.today().isoformat())
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            error("Invalid date. Use YYYY-MM-DD.")
            return
        if parsed_date > date.today():
            error("Future dates are not allowed.")
            return

        date_str = parsed_date.isoformat()

        amt_raw = prompt(f"Amount ({RUPEE})")
        try:
            amount = float(amt_raw)
            if amount <= 0: raise ValueError
        except ValueError:
            error("Amount must be a positive number.")
            return

        print(clr("  Categories: " + " / ".join(f"{i+1}.{c}" for i, c in enumerate(CATEGORIES)), C.DIM))
        category = self._resolve_category(prompt("Category (name or number)", default="food"))
        if not category:
            error(f"Category must be one of: {', '.join(CATEGORIES)}")
            return

        note = prompt("Note (optional)", default="")

        self.expenses.append({
            "id": self.next_id, "date": date_str,
            "amount": amount, "category": category, "note": note,
        })
        self.next_id += 1
        self.save()
        success(f"Added — {RUPEE}{amount:.2f} [{category}] on {date_str}")

        if self.budget:
            spent = self._total(self._month_expenses(date_str[:7]))
            if spent > self.budget:
                print(clr(f"  🚨 BUDGET EXCEEDED! {RUPEE}{spent:.2f} / {RUPEE}{self.budget:.2f}", C.RED, C.BOLD))

    def edit_expense(self):
        self.view_expenses()
        if not self.expenses:
            return
        raw = prompt("\n  Enter expense ID to edit (0 to cancel)")
        if not raw.isdigit() or int(raw) == 0:
            info("Cancelled.")
            return
        eid = int(raw)
        matches = [e for e in self.expenses if e["id"] == eid]
        if not matches:
            error(f"No expense with ID {eid}.")
            return
        e = matches[0]

        print(clr(f"\n  Editing ID {eid} — press Enter to keep current value.", C.CYAN, C.BOLD))

        date_raw = prompt("Date (YYYY-MM-DD)", default=e["date"])
        try:
            parsed_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
        except ValueError:
            error("Invalid date.")
            return
        if parsed_date > date.today():
            error("Future dates are not allowed.")
            return

        amt_raw = prompt(f"Amount ({RUPEE})", default=e["amount"])
        try:
            amount = float(amt_raw)
            if amount <= 0: raise ValueError
        except ValueError:
            error("Amount must be positive.")
            return

        print(clr("  Categories: " + " / ".join(f"{i+1}.{c}" for i, c in enumerate(CATEGORIES)), C.DIM))
        category = self._resolve_category(prompt("Category", default=e["category"]))
        if not category:
            error("Invalid category.")
            return

        note = prompt("Note", default=e.get("note", ""))

        e["date"], e["amount"], e["category"], e["note"] = parsed_date.isoformat(), amount, category, note
        self.save()
        success(f"Updated ID {eid} — {RUPEE}{amount:.2f} [{category}]")

    def view_expenses(self, expenses=None):  # accepts optional subset, no state mutation
        data = self.expenses if expenses is None else expenses
        if not data:
            info("No expenses yet.")
            return
        print(clr("\n  ── All Expenses ──", C.CYAN, C.BOLD))
        print(clr(f"  {'ID':<4} {'Date':<12} {'Category':<12} {'Amount':>10}  Note", C.WHITE, C.BOLD))
        divider()
        for e in sorted(data, key=lambda x: x["date"], reverse=True):
            color  = CAT_COLORS.get(e["category"], C.WHITE)
            amt    = f"{RUPEE}{e['amount']:.2f}"
            print(f"  {clr(str(e['id']).ljust(4), C.DIM)} {e['date']:<12} "
                  f"{clr(e['category'].ljust(12), color)} {clr(amt.rjust(10), C.CYAN)}  "
                  f"{clr(e.get('note',''), C.DIM)}")
        divider()
        print(clr(f"  {'TOTAL':>30}  {RUPEE}{self._total(data):.2f}", C.WHITE, C.BOLD))

    def view_summary(self):
        if not self.expenses:
            info("No expenses yet.")
            return
        total  = self._total()
        by_cat = self._by_category()
        print(clr("\n  ── Category Summary ──", C.CYAN, C.BOLD))
        print(clr(f"  {'Category':<12} {'Spent':>10}  {'Share':>7}  Bar", C.WHITE, C.BOLD))
        divider()
        for cat, amt in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
            pct   = amt / total * 100 if total else 0
            bar   = "▓" * int(pct / 5)
            color = CAT_COLORS.get(cat, C.WHITE)
            print(f"  {clr(cat.ljust(12), color)} {clr(f'{RUPEE}{amt:.2f}'.rjust(10), C.CYAN)}  "
                  f"{pct:>6.1f}%  {clr(bar, color)}")
        divider()
        top = max(by_cat, key=by_cat.get)
        print(clr(f"  TOTAL  {RUPEE}{total:.2f}", C.WHITE, C.BOLD))
        print(clr(f"  Highest: {top.upper()} ({RUPEE}{by_cat[top]:.2f})", C.YELLOW, C.BOLD))
        if self.budget:
            print()
            self._budget_bar(self._total(self._month_expenses()), self.budget)

    def monthly_view(self):
        if not self.expenses:
            info("No expenses yet.")
            return
        by_month = defaultdict(list)
        for e in self.expenses:
            by_month[e["date"][:7]].append(e)
        print(clr("\n  ── Monthly Breakdown ──", C.CYAN, C.BOLD))
        for month in sorted(by_month.keys(), reverse=True):
            entries = by_month[month]
            total   = self._total(entries)
            print(clr(f"\n  {month}  —  {len(entries)} expenses  —  {RUPEE}{total:.2f}", C.WHITE, C.BOLD))
            for e in sorted(entries, key=lambda x: x["date"]):
                print(clr(f"    {e['date']}  {e['category']:<10}  {RUPEE}{e['amount']:.2f}  {e.get('note','')}", C.DIM))
            if self.budget and month == date.today().isoformat()[:7]:
                print()
                self._budget_bar(total, self.budget)

    def filter_by_category(self):
        print(clr("  Categories: " + " / ".join(f"{i+1}.{c}" for i, c in enumerate(CATEGORIES)), C.DIM))
        category = self._resolve_category(prompt("Filter by category"))
        if not category:
            error("Unknown category.")
            return
        filtered = [e for e in self.expenses if e["category"] == category]
        if not filtered:
            info(f"No expenses in '{category}'.")
            return
        self.view_expenses(filtered)  # FIX: pass subset directly, no state swap

    def delete_expense(self):
        self.view_expenses()
        if not self.expenses:
            return
        raw = prompt("\n  Enter expense ID to delete (0 to cancel)")
        if not raw.isdigit() or int(raw) == 0:
            info("Cancelled.")
            return
        eid = int(raw)
        match = [e for e in self.expenses if e["id"] == eid]
        if not match:
            error(f"No expense with ID {eid}.")
            return
        e = match[0]
        confirm = prompt(f"Delete '{e.get('note') or e['category']}' ({RUPEE}{e['amount']:.2f})? (y/n)", default="n")
        if confirm.lower() == "y":
            self.expenses = [x for x in self.expenses if x["id"] != eid]
            self.save()
            success("Expense deleted.")
        else:
            info("Cancelled.")

    def set_budget(self):
        print(clr("\n  ── Monthly Budget ──", C.CYAN, C.BOLD))
        if self.budget:
            info(f"Current: {RUPEE}{self.budget:.2f}")
        raw = prompt(f"Set monthly budget ({RUPEE})", default=self.budget or "")
        if not raw:
            info("Budget unchanged.")
            return
        try:
            budget = float(raw)
            if budget <= 0: raise ValueError
        except ValueError:
            error("Enter a valid positive amount.")
            return
        self.budget = budget
        self.save()
        success(f"Budget set to {RUPEE}{budget:.2f}")

    def spending_insights(self):
        if not self.expenses:
            info("No expenses yet.")
            return

        total    = self._total()
        by_cat   = self._by_category()
        top_cat  = max(by_cat, key=by_cat.get)
        top5     = sorted(self.expenses, key=lambda x: x["amount"], reverse=True)[:5]

        dates    = sorted(set(e["date"] for e in self.expenses))
        try:
            day_span = max((datetime.strptime(dates[-1], "%Y-%m-%d") -
                            datetime.strptime(dates[0],  "%Y-%m-%d")).days + 1, 1)
        except ValueError:
            day_span = 1
        avg_daily = total / day_span

        today_day     = date.today().day
        days_in_month = calendar.monthrange(date.today().year, date.today().month)[1]
        month_spent   = self._total(self._month_expenses())
        projected     = (month_spent / today_day) * days_in_month if today_day > 0 else 0

        # Most expensive day calculation
        day_totals = defaultdict(float)
        for e in self.expenses:
            day_totals[e["date"]] += e["amount"]
        max_day = max(day_totals, key=day_totals.get)
        max_day_amount = day_totals[max_day]

        streak = self._streak()

        # Health score
        score = 100
        if self.budget and self.budget > 0:
            usage = month_spent / self.budget
            if   usage > 1.0: score -= 30
            elif usage > 0.9: score -= 15
            elif usage > 0.8: score -= 5
        top_pct = by_cat[top_cat] / total if total else 0
        if   top_pct > 0.6: score -= 15
        elif top_pct > 0.5: score -= 8
        score = max(0, min(100, score))
        if   score >= 85: health_label, hc = "Excellent 🟢", C.GREEN
        elif score >= 65: health_label, hc = "Good 🟡",      C.YELLOW
        else:             health_label, hc = "Needs Work 🔴", C.RED

        print(clr("\n  ── Spending Insights ──", C.CYAN, C.BOLD))
        divider()
        print(clr(f"  📊 Total Expenses:        ", C.WHITE) + clr(len(self.expenses), C.CYAN, C.BOLD))
        print(clr(f"  💰 Total Spent:           ", C.WHITE) + clr(f"{RUPEE}{total:.2f}", C.CYAN, C.BOLD))
        print(clr(f"  📅 Avg Daily Spend:       ", C.WHITE) + clr(f"{RUPEE}{avg_daily:.2f}", C.CYAN, C.BOLD))
        print(clr(f"  🏆 Highest Category:      ", C.WHITE) + clr(f"{top_cat.title()} ({RUPEE}{by_cat[top_cat]:.2f})", C.YELLOW, C.BOLD))
        print(clr(f"  📅 Most Expensive Day:    ", C.WHITE) + clr(f"{max_day} ({RUPEE}{max_day_amount:.2f})", C.YELLOW, C.BOLD))
        projected_val = clr(f"{RUPEE}{projected:.2f}", C.MAGENTA, C.BOLD) if today_day >= 3 else clr("Calculating... (3d min)", C.DIM)
        print(clr(f"  📈 Projected Month-End:   ", C.WHITE) + projected_val)
        if streak > 0:
            print(clr(f"  🔥 Tracking Streak:       ", C.WHITE) + clr(f"{streak} day{'s' if streak != 1 else ''}", C.YELLOW, C.BOLD))
        divider()
        print(clr("  Top 5 Largest Expenses:", C.WHITE, C.BOLD))
        for i, e in enumerate(top5, 1):
            label = e["category"].title() + (f" — {e['note']}" if e.get("note") else "")
            print(clr(f"  {i}. {RUPEE}{e['amount']:.2f}  {label}", C.DIM))
        divider()
        print(clr(f"  Financial Health Score:  ", C.WHITE, C.BOLD) + clr(f"{score}/100  {health_label}", hc, C.BOLD))
        # Rule-based advice
        if top_pct > 0.5:
            print(clr(f"\n  💡 {top_pct*100:.0f}% of spending is on {top_cat} — worth tracking closely.", C.YELLOW))
        if self.budget and month_spent > self.budget * 0.8:
            remaining = self.budget - month_spent
            days_left = days_in_month - today_day
            per_day   = remaining / days_left if days_left > 0 else 0
            print(clr(f"  💡 {RUPEE}{remaining:.0f} left — aim for {RUPEE}{per_day:.0f}/day to stay on track.", C.YELLOW))

        # Financial personality
        PERSONALITIES = {
            "food":     ("🍔", "Foodie Explorer",   "You enjoy spending on meals and snacks.\n  Food is clearly central to your daily experience."),
            "travel":   ("🚕", "Frequent Traveler", "You’re always on the move.\n  Rides, metro, fuel — the city is your playground."),
            "recharge": ("📱", "Digital Native",    "Connectivity is your top priority.\n  You keep your devices and subscriptions running."),
            "other":    ("📚", "Mindful Spender",   "Your biggest spend is on essentials and learning.\n  You invest in things that matter beyond daily habits."),
        }
        if top_pct < 0.35:
            emoji, title, desc = ("💰", "Balanced Spender", "Your spending is spread evenly across categories.\n  You maintain a balanced budget without specific spikes.")
            intro_text = f"  Your highest category represents {top_pct*100:.0f}% of your spending."
        else:
            emoji, title, desc = PERSONALITIES.get(top_cat, ("💰", "Balanced Spender", "Your spending is spread across categories."))
            intro_text = f"  {top_pct*100:.0f}% of your spending is on {top_cat}."

        print(clr("\n  " + "═" * 38, C.DIM))
        print(clr("  FINANCIAL PERSONALITY", C.WHITE, C.BOLD))
        print(clr("  " + "═" * 38, C.DIM))
        print(f"\n  {clr(f'{emoji}  {title}', C.CYAN, C.BOLD)}\n")
        print(clr(intro_text, C.WHITE))
        for line in desc.split("\n"):
            print(clr(f"  {line}", C.DIM))
        print()

    def generate_report(self):
        today       = date.today().isoformat()
        total       = self._total()
        month_spent = self._total(self._month_expenses())
        by_cat      = self._by_category()
        top_cat     = max(by_cat, key=by_cat.get) if by_cat else "N/A"
        top5        = sorted(self.expenses, key=lambda x: x["amount"], reverse=True)[:5]

        today_day     = date.today().day
        days_in_month = calendar.monthrange(date.today().year, date.today().month)[1]
        projected     = (month_spent / today_day) * days_in_month if today_day else 0
        projected_str = f"{RUPEE}{projected:.2f}" if today_day >= 3 else "Calculating... (3d min)"

        if not self.budget:
            budget_status = "Not set"
        else:
            pct = month_spent / self.budget * 100
            if   pct > 100: budget_status = f"EXCEEDED ({pct:.1f}% used)"
            elif pct > 80:  budget_status = f"Warning — {pct:.1f}% used"
            else:           budget_status = f"Within budget — {pct:.1f}% used"

        lines = [
            "=" * 44,
            "  STUDENT EXPENSE REPORT",
            f"  Generated: {today}",
            "=" * 44,
            "",
            f"  Total Expenses      : {len(self.expenses)}",
            f"  Total Spent         : {RUPEE}{total:.2f}",
            f"  This Month          : {RUPEE}{month_spent:.2f}",
            f"  Projected Month-End : {projected_str}",
            f"  Budget Status       : {budget_status}",
            "",
            "─" * 44,
            "  CATEGORY BREAKDOWN",
            "─" * 44,
        ]
        for cat, amt in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
            pct = amt / total * 100 if total else 0
            lines.append(f"  {cat.title():<12}  {RUPEE}{amt:.2f}  ({pct:.1f}%)")
        lines += ["", "─" * 44, "  TOP 5 EXPENSES", "─" * 44]
        for i, e in enumerate(top5, 1):
            lines.append(f"  {i}. {RUPEE}{e['amount']:.2f}  [{e['category'].title()}]  {e.get('note','')}  ({e['date']})")
        lines += [
            "", "─" * 44,
            f"  Highest Spending: {top_cat.title()} ({RUPEE}{by_cat.get(top_cat, 0):.2f})",
            "─" * 44, "",
            "  Generated by Student Expense Tracker",
            "  github.com/codewithabhiishek",
            "=" * 44,
        ]

        filename = f"expense_report_{today}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:  # FIX: utf-8 for ₹
                f.write("\n".join(lines))
            success(f"Report saved → {filename}")
        except OSError as e:
            error(f"Could not generate report: {e}")
        print()
        for line in lines:
            style = (C.DIM,) if (line.startswith("─") or line.startswith("=")) else ()
            print(clr(f"  {line}", *style))

    def export_csv(self):
        today    = date.today().isoformat()
        filename = f"expenses_{today}.csv"
        fields   = ["id", "date", "category", "amount", "note"]
        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:  # FIX: utf-8 for ₹
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for e in sorted(self.expenses, key=lambda x: x["date"]):
                    writer.writerow({k: e.get(k, "") for k in fields})
            success(f"Exported {len(self.expenses)} expenses → {filename}")
        except OSError as e:
            error(f"Export failed: {e}")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    def startup_summary(self):
        count       = len(self.expenses)
        month_spent = self._total(self._month_expenses())
        total       = self._total()
        streak      = self._streak()

        src = "expenses.json" if os.path.exists(DATA_FILE) else "sample data"
        print(clr(f"  Loaded {count} expense{'s' if count != 1 else ''} from {src}", C.DIM), end="")
        if streak > 0:
            print(clr(f"  🔥 {streak}-day streak", C.YELLOW, C.BOLD))
        else:
            print()

        if self.budget and self.budget > 0:
            actual_pct = month_spent / self.budget
            bar_pct    = min(actual_pct, 1.0)
            fill       = int(bar_pct * 20)
            bar        = "█" * fill + "░" * (20 - fill)
            bar_color  = C.RED if actual_pct >= 1.0 else C.YELLOW if actual_pct >= 0.8 else C.GREEN
            print(clr(f"  Current Budget:   {RUPEE}{self.budget:.0f}", C.WHITE, C.BOLD))
            print(clr(f"  Spent This Month: {RUPEE}{month_spent:.2f}  ({actual_pct*100:.1f}%)", bar_color, C.BOLD))
            print(clr(f"  [{bar}] {actual_pct*100:.0f}%", bar_color))
            if actual_pct >= 1.0:
                print(clr("  🚨 BUDGET EXCEEDED!", C.RED, C.BOLD))
            elif actual_pct >= 0.8:
                print(clr("  ⚠️  Budget warning!", C.YELLOW, C.BOLD))
        else:
            print(clr(f"  This month: {RUPEE}{month_spent:.2f}  •  All time: {RUPEE}{total:.2f}", C.WHITE))

    # ── Visual screens ────────────────────────────────────────────────────────
    def where_did_money_go(self):
        """ASCII category breakdown — 'Where Did My Money Go?'"""
        if not self.expenses:
            info("No expenses yet.")
            return
        total  = self._total()
        by_cat = self._by_category()
        BAR_W  = 28   # max bar width in chars

        print(clr("\n  ── Where Did My Money Go? ──", C.CYAN, C.BOLD))
        divider()
        print(clr(f"  {'Category':<10}  {'Bar':<{BAR_W+2}}  {'Amount':>9}  Share", C.WHITE, C.BOLD))
        divider()
        for cat, amt in sorted(by_cat.items(), key=lambda x: x[1], reverse=True):
            pct   = amt / total if total else 0
            fill  = int(pct * BAR_W)
            bar   = "█" * fill + "░" * (BAR_W - fill)
            color = CAT_COLORS.get(cat, C.WHITE)
            print(f"  {clr(cat.title().ljust(10), color)}  "
                  f"{clr(bar, color)}  "
                  f"{clr(f'{RUPEE}{amt:.2f}'.rjust(9), C.CYAN)}  "
                  f"{clr(f'{pct*100:.1f}%', C.DIM)}")
        divider()
        print(clr(f"  {'TOTAL':<10}  {'':>{BAR_W+2}}  {RUPEE}{total:.2f}", C.WHITE, C.BOLD))

    def spending_timeline(self):
        """ASCII bar chart: daily spend for the last 14 days."""
        if not self.expenses:
            info("No expenses yet.")
            return

        today  = date.today()
        days   = [(today - timedelta(days=i)) for i in range(13, -1, -1)]  # oldest → newest
        by_day = defaultdict(float)
        for e in self.expenses:
            by_day[e["date"]] += e["amount"]

        daily_vals = [by_day.get(d.isoformat(), 0.0) for d in days]
        max_val    = max(daily_vals) if any(daily_vals) else 1.0
        BAR_W      = 30

        print(clr("\n  ── Spending Timeline (last 14 days) ──", C.CYAN, C.BOLD))
        divider()
        for d, val in zip(days, daily_vals):
            label = d.strftime("%b %d")
            fill  = max(1, int((val / max_val) * BAR_W)) if (val > 0 and max_val) else 0  # FIX: tiny values still show 1 char
            bar   = "▓" * fill
            amt_str = f"{RUPEE}{val:.0f}" if val else "—"
            # highlight today
            color = C.CYAN if d == today else (C.GREEN if val > 0 else C.DIM)
            tag   = clr(" ← today", C.YELLOW, C.BOLD) if d == today else ""
            print(f"  {clr(label, C.DIM)}  {clr(f'{bar:<{BAR_W}}', color)}  {clr(amt_str.rjust(6), color)}{tag}")
        divider()
        spent_period = sum(daily_vals)
        active_days  = sum(1 for v in daily_vals if v > 0)
        print(clr(f"  14-day total: {RUPEE}{spent_period:.2f}  •  Active days: {active_days}", C.WHITE, C.BOLD))

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        MENU = [
            ("Add expense",         self.add_expense),
            ("View all expenses",   self.view_expenses),
            ("Edit expense",        self.edit_expense),
            ("Category summary",    self.view_summary),
            ("Monthly breakdown",   self.monthly_view),
            ("Filter by category",  self.filter_by_category),
            ("Delete an expense",   self.delete_expense),
            ("Set monthly budget",  self.set_budget),
            ("Spending insights",   self.spending_insights),
            ("Where did money go?", self.where_did_money_go),
            ("Spending timeline",   self.spending_timeline),
            ("Generate report",     self.generate_report),
            ("Export to CSV",       self.export_csv),
            ("Save & Exit",         None),
        ]

        while True:
            clear()
            print(clr("""
  ╔════════════════════════════════════════╗
  ║             RUPEETRACK 💸              ║
  ║ Smart Student Expense Management System║
  ╚════════════════════════════════════════╝""", C.CYAN, C.BOLD))
            divider()
            self.startup_summary()
            divider()
            print()
            for i, (label, _) in enumerate(MENU, 1):
                print(f"  {clr(f'{i:>2}.', C.CYAN, C.BOLD)} {label}")
            print()

            choice = prompt("Choose an option")
            if not choice.isdigit() or not (1 <= int(choice) <= len(MENU)):
                error("Pick a number from the menu.")
                input(clr("  Press Enter to continue...", C.DIM))
                continue

            label, fn = MENU[int(choice) - 1]
            if fn is None:
                self.save()
                clear()
                print(clr("\n  Data saved. Bye! Track every rupee. 👋\n", C.CYAN, C.BOLD))
                sys.exit(0)

            print()
            fn()
            print()
            input(clr("  Press Enter to continue...", C.DIM))


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ExpenseTracker().run()