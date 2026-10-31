"""PAST readings for the free preview ('Your months before this Diwali').

PAST[work_type][tone] = [v1, v2, v3]; each text is 7 sentences, each at most 18 words.
Plain daily English, past tense, recognition reading, no advice.
"""

PAST_HEADINGS = {"good": "A good time", "steady": "A mixed time", "careful": "A slower, costlier time"}

PAST = {
    "job": {
        "good": [
            "Things went your way in many small and big matters. Your seniors showed more trust in you. More money came in than in the months before. You ran around a lot for work, and it paid off. A small disagreement at home was over quickly. You probably spent on a home item you had wanted for long. All in all, it was a time worth remembering.",
            "This was a bright time, with something good happening often. A task you finished well earned you thanks. You spent on comfort and did not regret it. A small family function brought everyone together. Friends stayed close, and you enjoyed their company. A vehicle or home item was fixed or bought with ease. On the whole, you ended these months in a better place.",
            "These months felt easy and kind to you. Your seniors praised a task you handed in on time. Your salary came in full, and some extra came with it. A cousin's function at home was warm and cheerful. You and a colleague shared lunch and a good laugh most days. One busy week was tiring, but it ended well. Looking back, these months were smooth and pleasant.",
        ],
        "steady": [
            "These months had ups and downs in about equal share. Your work went on at an even pace, with one kind word from a senior. Money in hand stayed about the same as before. A family function brought everyone together for an evening. You put off buying a home item and did not mind. One small disagreement with a colleague was soon forgotten. Overall, it was an even mix of good and slow days.",
            "These months were neither great nor poor, just mixed. A senior gave you a task that was hard but fair. You spent a bit more than planned on the home. Friends from work met you twice, and both times were fun. A few weeks were busy and tiring. Your salary came on time, though it did not go far. All in all, the good and the slow days came about equal.",
            "Some days went well and some did not, and it balanced out. Your colleagues were friendly, and you shared tea and small talk. A function at a relative's home asked for some time and money. You bought a small item for the home, and it was useful. A short talk with a senior at work went better than you thought. You and a family member disagreed over a small matter, and it ended soon. Overall, these months were fair and even.",
        ],
        "careful": [
            "These months were slower, and costs came up more than you hoped. Money in hand ran thin before the month ended. A family function took more money than you had planned. Work moved slowly, and your seniors were busy and had little time for you. A colleague helped you finish a task that was stuck. You ran around a lot, and the weeks were tiring. It was a slow time, though one kind colleague made it easier.",
            "This was a slower time, and your spending went up. A repair or purchase for the home cost more than expected. A small disagreement with someone at work took a few days to settle. Your extra work was not noticed much by seniors. An elder in the family gave you good advice, and it helped. Days were busy and tiring, and rest was short. These months were costly, but you came through them with kind support.",
            "These months moved slowly and felt costly. Your pay came on time, but bills ate most of it. A friend at work helped you when you were stuck. Travel for a family function cost more time and money. You probably put off a home purchase you had wanted. A small misunderstanding with a colleague left a little distance. It was a slow time, yet a few good people made it easier.",
        ],
    },
    "business": {
        "good": [
            "Business ran well, and these months brought you good news. Orders came in briskly, and payments followed on time. Stock moved fast, and costs stayed in check. A family function was joyful, and you gave it good time. A trip for work turned out useful and brought new contacts. Other traders spoke well of you and shared good tips. In all, your business ended these months in a better place.",
            "These were bright months, with plenty to smile about. A big customer paid in full, and ahead of time. You bought stock at a fair rate and sold it quickly. Someone close to you disagreed on a small matter, and it ended fast. A family trip was easy and happy. Busy days left you tired, but the shop stayed lively. On the whole, these months rewarded your effort.",
            "Things went your way at the shop and at home. Repeat customers came back and brought their friends. Late payments were fewer, and cash was easier to find. You probably cleared an old bill and were glad to have it done. A family function brought relatives close and in good cheer. A fellow trader helped you with a big order. These months left you in a stronger place.",
        ],
        "steady": [
            "Your business had ups and downs in about equal share. Some orders came briskly, and some payments came late. Stock costs went up a little, and you managed them. A family function took a few days of your time. A trip for work was useful, though a bit tiring. A trader friend gave you a good tip, and it worked. Overall, it was a mix of good and slow weeks.",
            "These months were mixed, with no big win and no big loss. Orders stayed flat, but a few new customers came in. A payment you waited for came in at last. Prices of goods moved up and down, and you kept your pace. You and someone close had a small misunderstanding that passed soon. A visit to relatives was warm and cost little. In all, the months were fair and even.",
            "Some weeks were busy and some were quiet at the shop. Sales were about the same as before. You spent a little more on stock than you planned. A family function brought everyone together for a happy evening. Other traders met you, and talk of the market was useful. A small disagreement with a helper at the shop ended with a smile. Taken together, it was an even mix.",
        ],
        "careful": [
            "Things took longer, and the costs were higher. Payments came late, and your earnings stayed flat. Travel, home things and comfort cost more than expected. Work moved slowly, and new orders were fewer than you hoped. Running around for work or family left you tired. One good order came through and helped a little. Things were slower, but that small gain made these months easier to carry.",
            "These months took more effort than they paid back. Your income came in smaller amounts than before. A small difference of opinion with someone close was soon settled. Your days were busy and left little time to rest. A family function or visit cost more time and money than planned. A friend or relative helped you with a small bill. These months were costly, yet you ended them with some help.",
            "These months were slow, and money moved with difficulty. Some payments were late, and you waited a long time. Stock cost more, and you could not raise your prices. A trip for family cost more than you had planned. Another trader helped you with stock on easy terms. You and someone close had a small misunderstanding, and it took time to settle. It was a slow time, but kind people stood by you.",
        ],
    },
    "student": {
        "good": [
            "Things went well for you in your studies and outside them. Your new term began well, and you settled in fast. A senior or teacher guided you on the right subject choice. You had a small argument with a family member, and it was over quickly. Your parents helped with a fee or a big expense without fuss. You probably got a new phone, laptop or other gadget you had wanted. Looking back, these months were ones you were glad to have had.",
            "This was a happy time, with good news from several sides. Busy exam days were tiring, but the result made it worth it. Your marks or grades went up compared with before. Friends came together for a festival, and you enjoyed it. A placement talk or a work chance moved a step ahead. Your parents were glad and gave you some extra money for Diwali. On the whole, you reached the end of these months with a smile.",
            "These months were lively, and most things went right. Your teachers praised your notes and your effort. You and your hostel or home friends shared many happy evenings. Your parents sent pocket money on time, and some extra. You bought new earphones that you had liked for long. A small argument with a friend ended with a laugh. Overall, you finished these months feeling good about yourself.",
        ],
        "steady": [
            "Your months went up and down in about equal share. Classes went on at an even pace, and one teacher was very kind. Pocket money was enough, though not much was left over. You talked with a senior about internships and placements. A small argument with a friend was soon forgotten. Some exam days were busy and tiring. On the whole, it was an even mix of easy and hard days.",
            "This was a mixed time, with good days and slow days. You did well in one test and poorly in another. Life at the hostel or home was cheerful and busy. Your parents gave you pocket money, but you spent it fast. You thought about a small purchase but kept it for later. A friend and you had a small misunderstanding that passed. In all, the good and the hard days came about equal.",
            "These months were neither easy nor hard. A teacher explained a tough topic, and it finally made sense. Your friends and you went out once, and it was fun. Your parents called often and asked how you were doing. A talk about first work came up, and you took notes. Late nights before a test were tiring. At the end, you had a fair share of both good and slow days.",
        ],
        "careful": [
            "These months were slower and costlier than you wanted. Studies took more time, and one test went below your hopes. Pocket money ran out before the month did. Your parents helped with an extra amount without much fuss. A gadget or book you needed cost more than planned. Late nights before exams were tiring. It was a slow time, and you got through it with some help.",
            "This was a slower time, and spending went up. A teacher gave you extra time to finish your work. A small argument with a friend left you quiet for some days. Your hostel or home bills and food costs went up. A talk about work or a placement was put off. A senior or friend helped you with notes, and it went fine. These months were costly, yet people around you made them easier.",
            "These months moved slowly and cost more than expected. Exam days were busy and left you very tired. Your results were average, and you wanted better. You probably had to wait for your pocket money this time. A friend helped you with a small bill. A small misunderstanding at the hostel or home took a while to settle. It was a slow time, but you finished it stronger than you began.",
        ],
    },
    "home": {
        "good": [
            "These months were cheerful, with something nice happening often. A function at the temple or in the community went off well. Friends and neighbours stayed close, and you enjoyed their company. You spent on the festival and did not regret it. A repair at home was done with ease. An elder was kind to you and gave good advice. By the end, the weeks had left you content.",
            "These months were happy, with warm moments on many days. Relatives visited, and your home felt full of joy. Your neighbours joined you for a small function, and it went well. You spent on festival items and were happy with them. An elder gave you a good idea, and it worked. A small repair at home was done quickly. In all, these months left your family in good cheer.",
            "Things went smoothly for you and your family. A cousin or an aunt stayed with you, and everyone enjoyed it. The festival spending fit well within your plans. You bought a new item for the kitchen and liked it. Busy days passed with good company and tasty food. A small misunderstanding was cleared with one kind word. These months were pleasant, and you ended them smiling.",
        ],
        "steady": [
            "This time had ups and downs in about equal share. A neighbour or relative dropped in, and it was a warm visit. You bought something small for the home, and it was useful. Spending on the family went up a little for a festival. An elder gave advice, and you followed some of it. Some weeks were quiet and some were full. Overall, it was an even mix.",
            "These months were mixed, with good days and slow days. Relatives came to visit, and the days were lively. A function at the temple or nearby was pleasant but tiring. Festival shopping cost a little more than last time. An elder gave you advice, and you thought about it. A small fix at home was put off for later. Together, the months were fair and even.",
            "Some days were easy and some were hard. Neighbours dropped in for tea more than once. The home budget went up a bit for the festival. You bought a small thing for the kitchen, and it was useful. A small misunderstanding with a relative passed after a day. Busy days in the kitchen were tiring. On the whole, it was a fair balance.",
        ],
        "careful": [
            "These months were slower, and home costs went up. The festival and daily needs cost more than you had planned. A repair at home came up and took some money. Relatives visited, and the extra work was tiring. An elder in the family gave advice that helped. A neighbour was kind and shared a useful tip. It was a slow time, but your family stood by you.",
            "This was a costlier time than you wished for. Guests came and went, and your days were full. A function in the community asked for a gift and some time. Festival items cost more this time. A small misunderstanding with someone at home left things quiet for a while. A small gain came your way, and your elders supported you. These months were slow, and you ended them with kind support.",
            "These months moved slowly, with more spending than saving. Daily costs went up, and the festival added to them. A home item needed fixing, and it cost some money. Neighbours gathered for a function, and it went fine. An elder told you to go slowly, and that advice helped. Long busy days left you tired. It was a slow time, and your family made it easier.",
        ],
    },
}
