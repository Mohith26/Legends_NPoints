"""Seed realistic test data for pipeline testing."""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, RawPost

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/legends_npoints"

# Realistic parenting post templates grouped by topic area
TOPIC_POSTS = {
    "sleep": [
        ("My 8 month old won't sleep through the night", "We've tried everything - white noise, dark room, consistent bedtime routine. She still wakes up 3-4 times a night. I'm exhausted and running on fumes at work. Any tips from parents who've been through this?", ["Have you tried the Ferber method? It worked wonders for us.", "Check with your pediatrician, could be teething or growth spurt.", "We did sleep training at 6 months and it changed our lives."]),
        ("Sleep training - did it actually work for you?", "Considering CIO or Ferber method for our 10 month old. She's never slept more than 3 hours straight. I feel guilty but we can't keep going like this.", ["Ferber worked in 3 nights for us. Best decision ever.", "We tried gentle methods first - pick up put down worked eventually.", "Don't feel guilty. A well-rested parent is a better parent."]),
        ("Toddler suddenly refusing to go to bed", "Our 2.5 year old was sleeping great, then suddenly started screaming at bedtime. Takes 2 hours to get her down now. We haven't changed anything in the routine.", ["Could be a regression. They're common at this age.", "We dealt with this - turned out she was scared of the dark.", "Try moving bedtime later by 30 mins, she might not be tired enough."]),
        ("Co-sleeping to crib transition help", "We co-slept for 14 months and now trying to get baby in the crib. Every attempt ends in hours of crying. How did you transition?", ["We did it gradually - crib in our room first, then moved it.", "The floor bed was our bridge between co-sleeping and crib.", "It took us 2 weeks but consistency was key."]),
        ("Nap transitions are killing me", "Going from 2 naps to 1 and my toddler is a MESS. Overtired, cranky, won't eat. How long does this take?", ["Took us about 3 weeks to fully adjust.", "We did quiet time in place of the dropped nap.", "Push lunch earlier and do one long midday nap."]),
    ],
    "screen_time": [
        ("How much screen time do you actually allow?", "I know the AAP guidelines but I'm curious what real parents actually do. My 3 year old watches about 2 hours a day and I feel so guilty.", ["We do about an hour but honestly more on sick days.", "No screens before 2 was impossible for us. Don't beat yourself up.", "Quality matters more than quantity. Sesame Street > random YouTube."]),
        ("iPad addiction in my 5 year old", "My son throws massive tantrums when we take away the iPad. I'm worried we've created a monster. He sneaks it at night too.", ["We had to go cold turkey for a week. It was rough but worked.", "Set firm time limits with a visual timer they can see.", "Replace screen time with activities. It's hard at first but they adjust."]),
        ("Is Cocomelon actually bad for toddlers?", "My pediatrician told me to avoid fast-paced shows like Cocomelon. Is there actual research on this? My 18 month old loves it.", ["The concern is about attention span development with rapid scene changes.", "We switched to Bluey and Daniel Tiger. Much better quality content.", "Everything in moderation. One episode won't ruin your kid."]),
        ("Screen-free activities for rainy days", "We're stuck inside and I need ideas that don't involve a screen. My kids are 2 and 4.", ["Play dough, sensory bins, blanket forts!", "Treasure hunts around the house work great.", "Baking together - messy but they love it."]),
    ],
    "discipline": [
        ("Gentle parenting isn't working for my strong-willed child", "I've read all the books, taken courses, and tried everything gentle parenting suggests. My 4 year old still hits, throws things, and refuses to listen. Am I doing something wrong?", ["Strong-willed kids need firm boundaries WITH empathy.", "Gentle parenting doesn't mean permissive. You can still set limits.", "We had success with 'time-ins' instead of time-outs."]),
        ("How do you handle public tantrums?", "My 3 year old had a complete meltdown in Target today. Screaming, kicking, the works. I could feel everyone staring. I just left the cart and carried her out.", ["You did the right thing leaving. Safety first.", "I've been there. Other parents understand. The judgy ones can kick rocks.", "We use a warning system before outings - helps set expectations."]),
        ("Time outs - are they actually harmful?", "I keep seeing conflicting info. Some say time outs are fine, others say they're traumatic. My parents used them and I turned out fine, but I want to do better.", ["The research shows brief, calm time-outs are fine.", "It depends on HOW you do them. Punitive vs calm makes a big difference.", "We use 'calm down corners' - same concept but more positive framing."]),
        ("Setting boundaries with grandparents who undermine discipline", "My MIL gives my kids candy after I say no, lets them skip naps, and tells them mommy is too strict. I'm losing my mind.", ["This is a partner issue. Your spouse needs to address it.", "We had to limit unsupervised visits until boundaries were respected.", "Write down your rules and give them to grandparents. Make it clear."]),
    ],
    "feeding": [
        ("Picky eater - my kid only eats 5 foods", "My 3 year old only eats chicken nuggets, mac and cheese, applesauce, goldfish, and yogurt. I've tried everything. Pediatrician says he's growing fine but I'm stressed.", ["Look into Ellyn Satter's division of responsibility.", "Food therapy helped us when it got really bad.", "Keep offering new foods without pressure. It can take 20+ exposures."]),
        ("Breastfeeding is so much harder than anyone told me", "I'm 3 weeks postpartum and breastfeeding is agony. Cracked nipples, bad latch, baby losing weight. I feel like a failure.", ["See a lactation consultant ASAP! A bad latch can be fixed.", "Fed is best. Formula is perfectly fine if BF isn't working.", "It gets so much easier after 6 weeks. Hang in there."]),
        ("When did you start solids and how?", "Baby is 5.5 months and showing all readiness signs. Thinking about BLW but terrified of choking.", ["We did a combo of purees and BLW. Worked great.", "Take an infant CPR class first for peace of mind.", "Started at 6 months with soft stick-shaped foods. The gagging is normal."]),
        ("Meal prep ideas for toddlers", "I need easy, healthy meals I can batch cook. My toddler needs variety but I have no time.", ["Muffin tin meals with different foods in each cup.", "We meal prep mini meatballs, pasta, and roasted veggies on Sundays.", "Overnight oats and smoothie packs for quick breakfasts."]),
    ],
    "mental_health": [
        ("I love my kids but I miss my old life", "Is it normal to grieve your pre-kid life? I love being a mom but sometimes I miss sleeping in, spontaneous trips, and just being alone with my thoughts.", ["Completely normal. Mourning your old identity is part of the transition.", "I felt this way too. It doesn't make you a bad parent.", "Finding small pockets of 'you time' helps a lot."]),
        ("Postpartum anxiety is consuming me", "I can't stop worrying something terrible will happen to my baby. I check if she's breathing every 5 minutes. I can't sleep even when she sleeps. Is this normal new parent worry or something more?", ["This sounds like PPA. Please talk to your doctor.", "I had this exact experience. Medication helped me enormously.", "You're not crazy. PPD/PPA is so common and very treatable."]),
        ("Dad here - feeling invisible and useless", "My wife breastfeeds so I can't help with that. Baby only wants mom. I feel like I'm just here to do dishes and laundry. Does it get better?", ["It gets SO much better. Bond with baby through baths, walks, play.", "You're not useless - those dishes and laundry are essential support.", "Once baby starts solids, you can be more involved with feeding."]),
        ("Parenting burnout is real", "I'm touched out, talked out, and burnt out. Two kids under 4 and I have nothing left. I yelled at my toddler today and cried in the bathroom.", ["You need a break. Can anyone take the kids for a few hours?", "Therapy helped me learn to manage the overwhelm.", "You're not alone. This is the hardest job and you're doing it."]),
    ],
    "education": [
        ("Red-shirting kindergarten - worth it?", "My son has a late summer birthday. Debating whether to hold him back a year. He's academically ready but emotionally immature.", ["We held our August boy back and don't regret it at all.", "Talk to his preschool teachers - they see him with peers.", "Research shows the advantage fades by 3rd grade."]),
        ("How to teach a 4 year old to read", "My daughter is interested in letters and wants to learn. What programs or methods worked for your kids?", ["Bob Books and sight word flashcards worked for us.", "Don't push it. Read TO them lots and it'll click when ready.", "Teach letter sounds, not names. Makes reading easier."]),
        ("Montessori vs traditional preschool", "Torn between a Montessori program and our local preschool. The Montessori is 3x the cost. Is it worth it?", ["The teacher matters more than the method.", "We did Montessori and loved the independence it built.", "Save the money. A good traditional preschool is just as effective."]),
    ],
    "milestones": [
        ("My 2 year old isn't talking yet", "Only says about 5 words. Pediatrician referred us to speech therapy but said not to worry. How can I not worry?", ["Early intervention is amazing. We started at 22 months.", "My late talker is now the most talkative kid in class.", "Read read read to them. Narrate everything you do."]),
        ("When did your kid potty train?", "My 3 year old shows zero interest. Everyone says their kid trained at 2 and I feel like we're behind.", ["3 is totally normal! Don't compare to early trainers.", "We waited until 3.5 and it took only 3 days.", "The Oh Crap method worked for us when nothing else did."]),
        ("Walking at 16 months - should I be worried?", "My 16 month old still isn't walking independently. Cruises furniture fine but won't let go.", ["16 months is within normal range. Give it time.", "My kid didn't walk until 18 months and now runs everywhere.", "Talk to your pediatrician if you're concerned, but this sounds normal."]),
    ],
    "relationships": [
        ("Marriage struggling after baby", "We used to be best friends. Now we're just two exhausted people who argue about whose turn it is. Date nights feel impossible.", ["Couples therapy saved our marriage post-baby.", "Schedule weekly check-ins even if it's just 15 minutes.", "It gets better as the baby gets older. Survive the first year."]),
        ("Single parenting is the hardest thing I've ever done", "Doing this alone after divorce. Working full time, no family nearby. I barely have time to shower let alone maintain the house.", ["Look into local single parent support groups.", "You're doing an amazing job even when it doesn't feel like it.", "Accept every offer of help. There's no prize for doing it alone."]),
        ("How to handle unsolicited parenting advice", "Everyone from strangers to family has opinions on how I raise my kid. How do you deal with it without being rude?", ["'Thanks, I'll think about it' and then do whatever you want.", "I started saying 'our pediatrician is happy with how things are going.'", "Boundaries. You don't owe anyone an explanation."]),
    ],
    "safety": [
        ("Found out my toddler can climb out of the crib", "Woke up to my 20 month old standing next to my bed at 3am. Heart attack. Is it time for a toddler bed?", ["Time for a floor bed or toddler bed. Safety first.", "Lower the mattress to the ground as a temporary fix.", "We used a sleep sack to prevent climbing."]),
        ("Car seat battles with my 3 year old", "Every single car ride is a screaming fight about the car seat. I'm at my wit's end.", ["Non-negotiable safety item. Acknowledge feelings but stay firm.", "Special car-only toys or snacks helped us.", "Let them buckle themselves (with you checking). Giving control helps."]),
        ("Childproofing for a newly walking baby", "Where do I even start? What are the must-haves?", ["Outlet covers, cabinet locks, anchor furniture, gate for stairs.", "Get on their level and look for dangers from their perspective.", "The toilet lock is the one people forget but it's important."]),
    ],
    "daycare": [
        ("Daycare costs more than my mortgage", "We're paying $2400/month for one child. How is this sustainable? Seriously considering having one parent stay home.", ["We did the math and staying home actually saved money after taxes.", "Look into in-home daycares - usually half the cost.", "It does get cheaper as they age into preschool rooms."]),
        ("First day of daycare - I cried more than she did", "Dropped off my 12 week old today. Longest day of my life. She was fine apparently. I am not.", ["It gets easier. By week 2 you'll feel much better.", "The socialization benefits are real. She'll thrive.", "Your feelings are valid. It's so hard being away from them."]),
        ("Daycare illnesses - is this normal?", "My toddler has been sick literally every other week since starting daycare 2 months ago. RSV, hand foot mouth, stomach bugs, colds.", ["First year of daycare is notorious for this. Their immune system is building.", "It's called the 'daycare plague' for a reason.", "Silver lining: they'll be much healthier in kindergarten."]),
    ],
}

def seed_data():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    subreddits = ["Parenting", "Mommit", "daddit", "beyondthebump", "toddlers", "NewParents", "ScienceBasedParenting"]
    base_date = datetime(2025, 6, 1, tzinfo=timezone.utc)
    post_id = 0

    for topic_name, posts in TOPIC_POSTS.items():
        for title, body, comments in posts:
            for i in range(random.randint(3, 6)):  # duplicate across subreddits with variation
                post_id += 1
                subreddit = random.choice(subreddits)
                days_offset = random.randint(0, 300)
                upvotes = random.randint(50, 5000)

                post = RawPost(
                    reddit_id=f"test_{post_id:04d}",
                    subreddit=subreddit,
                    title=title if i == 0 else f"{title} [update]" if i == 1 else title + f" - {subreddit} perspective",
                    body=body,
                    top_comments=comments,
                    upvotes=upvotes,
                    url=f"https://reddit.com/r/{subreddit}/comments/test{post_id}",
                    author=f"test_user_{post_id}",
                    created_utc=base_date + timedelta(days=days_offset),
                )
                session.add(post)

    session.commit()
    total = session.query(RawPost).count()
    print(f"Seeded {total} posts across {len(subreddits)} subreddits")
    session.close()

if __name__ == "__main__":
    seed_data()
