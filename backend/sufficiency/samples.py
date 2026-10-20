# HotpotQA-style samples. Passages are SHORT PARAPHRASES for demo purposes:
# replace them with the exact text from the official dataset for your report.
SAMPLES = [
 {"id": "hp1", "question": "What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?",
  "answer": "Chief of Protocol",
  "gold": [
   {"title": "Kiss and Tell (1945 film)", "text": "Kiss and Tell is a 1945 American comedy film in which Shirley Temple portrayed Corliss Archer."},
   {"title": "Shirley Temple", "text": "Shirley Temple Black was an American actress who later held government positions, serving as ambassador and as Chief of Protocol, the first woman to hold that post."}],
  "distractors": [
   {"title": "Janet Waldo", "text": "Janet Waldo voiced Corliss Archer on radio."},
   {"title": "Meet Corliss Archer", "text": "A radio and television sitcom about a teenage girl."}]},
 {"id": "hp2", "question": "Musician and satirist Allie Goertz wrote a song about the Simpsons character Milhouse, who Matt Groening named after who?",
  "answer": "President Richard Nixon",
  "gold": [
   {"title": "Allie Goertz", "text": "Allie Goertz is a musician and satirist who wrote a song about the Simpsons character Milhouse."},
   {"title": "Milhouse Van Houten", "text": "Milhouse is a recurring character in The Simpsons, created by Matt Groening and named after President Richard Nixon."}],
  "distractors": [
   {"title": "Bart Simpson", "text": "Bart is the eldest child of the Simpson family."},
   {"title": "Springfield", "text": "Springfield is the fictional town where the show is set."}]},
 {"id": "hp3", "question": "Which magazine was started first, Arthur's Magazine or First for Women?",
  "answer": "Arthur's Magazine",
  "gold": [
   {"title": "Arthur's Magazine", "text": "Arthur's Magazine was an American literary periodical in Philadelphia, started in 1844."},
   {"title": "First for Women", "text": "First for Women is a woman's magazine started in 1989."}],
  "distractors": [
   {"title": "Philadelphia", "text": "Philadelphia is the largest city in Pennsylvania."},
   {"title": "Periodical", "text": "A periodical is published at regular intervals."}]},
]
