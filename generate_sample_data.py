"""Generate a synthetic demo dataset (data/emails.csv).

The data is template-based so the project runs out of the box. For real-world
accuracy, train on a public corpus instead (see README: "Using a real dataset").
"""
import csv
import random
from pathlib import Path

random.seed(42)

SPAM_TEMPLATES = [
    "Congratulations {name}! You have won a ${amount} gift card. Click {link} to claim your prize now!!!",
    "URGENT: your account has been suspended. Verify your password immediately at {link} or lose access.",
    "Get {drug} online without a prescription. Cheap prices, worldwide shipping, order today!",
    "Make ${amount} per week working from home. No experience needed. Limited spots, act now: {link}",
    "You have been selected for a free cruise. Reply YES to claim your free vacation today.",
    "FINAL NOTICE: claim your ${amount} lottery winnings. Send your bank details to receive the transfer.",
    "Dear friend, I am a prince and need your help to move ${amount} million. You will receive 30% commission.",
    "Lowest mortgage rates guaranteed! Refinance now and save thousands. Click here: {link}",
    "Hot singles in your area want to meet you tonight. Click {link} to chat for free!",
    "Your PayPal account is limited. Confirm your identity now: {link} Failure to do so will close your account.",
    "Earn bitcoin fast! Double your investment in 24 hours, 100% guaranteed returns. Join now {link}",
    "Exclusive offer: buy one get three FREE. Cheap replica watches, designer bags, huge discount. Order now!",
    "Free iPhone giveaway! You are our lucky visitor number 1,000,000. Click {link} and claim your reward.",
    "Increase your income with this one weird trick. Doctors hate it! Click {link} before it is deleted.",
    "Your package could not be delivered. Pay a small fee of ${small} at {link} to reschedule delivery.",
    "WINNER!! As a valued customer you have been selected to receive a ${amount} cash prize. Call {phone} now.",
    "Lose 20 pounds in 2 weeks with this miracle pill. Risk free trial, no diet needed, order today!",
    "Act now! Limited time offer. Unlimited credit, no credit check, instant approval, apply at {link}",
    "Security alert: unusual login detected. Click {link} to verify your bank account or it will be blocked.",
    "Viagra cialis cheap meds discount pharmacy no prescription required fast delivery {link}",
]

HAM_TEMPLATES = [
    "Hi {name}, are we still meeting tomorrow at {time} to go over the project report? Let me know if you need to reschedule.",
    "Please find attached the minutes from today's team meeting. Action items are listed at the bottom.",
    "Thanks for your help with the presentation yesterday. The client really liked the new slides.",
    "Reminder: the quarterly budget review is on {day} at {time} in conference room B.",
    "Hey, can you send me the notes from the lecture? I missed the last twenty minutes.",
    "Your order #{order} has shipped and should arrive by {day}. You can track it from your account page.",
    "Hi team, the sprint retrospective has moved to {day}. Please add your feedback to the shared document beforehand.",
    "Dinner on Saturday? Mom is making her lasagna and everyone is coming over around {time}.",
    "Attached is the invoice for last month's consulting work. Please let me know if anything looks incorrect.",
    "I reviewed your pull request and left a few comments. Mostly small naming changes, otherwise looks good.",
    "Can we push the call to {time}? I have a conflict with another meeting that ran over.",
    "Thank you for registering for the workshop. The session starts at {time} and the link will be shared on the day.",
    "Here is the schedule for next week's exams. Please check your timetable and contact the office with questions.",
    "Happy birthday {name}! Hope you have a wonderful day. Let's get lunch when you are back in the office.",
    "The server maintenance is complete and all services are running normally. Let us know if you notice any issues.",
    "Could you review the draft of the research paper before {day}? I have updated the references section.",
    "Your appointment is confirmed for {day} at {time}. Reply to this email if you need to make changes.",
    "Just checking in about the apartment lease. The landlord sent the renewal form and we need to sign by Friday.",
    "Great news, the proposal was approved. Let's schedule a kickoff meeting next week to plan the timeline.",
    "Your monthly statement is now available. Log in to your account on our website to view the details.",
    "I'm running late, stuck in traffic. Start without me and I'll join as soon as I get there.",
    "Here are the photos from the trip. I put them in the shared album, tell me if any are missing.",
    "Hi {name}, thanks for your interview yesterday. We would like to schedule a follow-up conversation next week.",
    "Reminder to submit your timesheet by end of day {day}. Contact payroll if you have trouble with the portal.",
]

NAMES = ["Alex", "Priya", "Sam", "Jordan", "Riya", "Chris", "Ananya", "Taylor", "Rahul", "Maria"]
LINKS = ["http://bit.ly/x9Fq2", "http://secure-login.example-verify.com", "www.win-prizes-now.biz",
         "http://claim-reward.top/abc", "https://tinyurl.com/free-gift", "http://account-check.xyz/login"]
DRUGS = ["pills", "meds", "tablets", "medication"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "next week"]
TIMES = ["9:30 AM", "11:00 AM", "2:00 PM", "3:30 PM", "5:00 PM", "7:30 PM"]

SPAM_SUBJECTS = ["You WON!!!", "Urgent account notice", "Free gift inside", "Make money fast", "Final notice",
                 "Cheap meds online", "Claim your reward", "Act now", "Verify your account", "Limited time offer"]
HAM_SUBJECTS = ["Meeting tomorrow", "Project update", "Re: notes", "Invoice attached", "Schedule change",
                "Lunch?", "Order shipped", "Quick question", "Feedback on draft", "Appointment confirmed"]


def fill(template):
    return template.format(
        name=random.choice(NAMES),
        amount=random.choice([500, 1000, 5000, 10000, 250000]),
        small=random.choice([1, 2, 3]),
        link=random.choice(LINKS),
        drug=random.choice(DRUGS),
        phone="0" + "".join(random.choice("0123456789") for _ in range(10)),
        time=random.choice(TIMES),
        day=random.choice(DAYS),
        order=random.randint(10000, 99999),
    )


def maybe_noise(text):
    r = random.random()
    if r < 0.15:
        return text.upper()
    if r < 0.25:
        return text.replace(".", "!")
    return text


def main(n_per_class=400):
    rows = []
    for _ in range(n_per_class):
        rows.append(("spam", random.choice(SPAM_SUBJECTS), maybe_noise(fill(random.choice(SPAM_TEMPLATES)))))
        rows.append(("ham", random.choice(HAM_SUBJECTS), fill(random.choice(HAM_TEMPLATES))))
    random.shuffle(rows)
    out = Path(__file__).parent / "data" / "emails.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["label", "subject", "text"])
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
