"""
OPSC OCS Prelims 2024 - Video with AI Voice Narration
Generates professional video with TTS audio for all 100 questions.
Uses edge-tts for high-quality AI voice narration.
"""

import os
import sys
import asyncio
import shutil
import subprocess
import json
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import edge_tts

# ── CONFIG ──────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1920, 1080
OUTPUT_DIR = "output"
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio_clips")
FRAMES_DIR = os.path.join(OUTPUT_DIR, "frames_v2")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "opsc_ocs_prelims_2024_with_audio.mp4")

# Voice config - Hindi male voice (professional, clear)
VOICE = "hi-IN-MadhurNeural"  # Hindi male - clear and professional
RATE = "+5%"  # Slightly faster for engaging pace

# Fonts
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "assets/fonts/arial.ttf"

# Colors
BG_DARK = (15, 15, 30)
BG_CARD = (25, 30, 55)
ACCENT_BLUE = (0, 150, 255)
ACCENT_GREEN = (0, 200, 100)
ACCENT_ORANGE = (255, 165, 0)
ACCENT_RED = (220, 50, 50)
TEXT_WHITE = (255, 255, 255)
TEXT_LIGHT = (200, 210, 230)
TEXT_DIM = (140, 150, 170)
GOLD = (255, 215, 0)
PURPLE = (150, 100, 255)

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)

# ── ALL 100 QUESTIONS ───────────────────────────────────────────────────
QUESTIONS = [
    {
        "q_no": 1,
        "question": "Match the following:\nList-I (Authors) → List-II (Books)\n1) A L Basham → a) India as a secular state\n2) Donald E Smith → b) The wonder that was India\n3) Rudolph & Rudolph → c) Government and politics of India\n4) WH Morris Jones → d) In pursuit of Lakshmi",
        "options": ["(A) b a d c", "(B) a c b d", "(C) d b a c", "(D) d c b a"],
        "answer": "D",
        "explanation": "The correct matching is: A L Basham wrote The Wonder That Was India, Donald E Smith wrote India as a secular state, Rudolph and Rudolph wrote In pursuit of Lakshmi, and WH Morris Jones wrote Government and politics of India. So the order is d, c, b, a.",
        "narration_q": "प्रश्न 1. लेखकों को उनकी पुस्तकों से मिलाइए। A L Basham, Donald E Smith, Rudolph and Rudolph, और W H Morris Jones.",
        "narration_a": "सही उत्तर है विकल्प D. A L Basham ने The Wonder That Was India लिखी। Donald E Smith ने India as a secular state लिखी। Rudolph and Rudolph ने In pursuit of Lakshmi लिखी। और W H Morris Jones ने Government and politics of India लिखी।"
    },
    {
        "q_no": 2,
        "question": "The 15th Finance Commission recommended a health grant architecture focusing on",
        "options": ["(A) Health cess consolidation into GST", "(B) States' debt takeover by Centre", "(C) Universal health premium", "(D) Urban/rural health infrastructure and primary health care strengthening"],
        "answer": "D",
        "explanation": "The 15th Finance Commission recommended health grants focusing on strengthening urban and rural health infrastructure, and primary healthcare.",
        "narration_q": "प्रश्न 2. 15वें वित्त आयोग ने स्वास्थ्य अनुदान में किस पर ध्यान देने की सिफारिश की?",
        "narration_a": "सही उत्तर है विकल्प D. शहरी और ग्रामीण स्वास्थ्य अवसंरचना और प्राथमिक स्वास्थ्य सेवा को मजबूत करना। 15वें वित्त आयोग ने, जिसकी अध्यक्षता N K Singh ने की, COVID-19 के बाद जमीनी स्तर पर स्वास्थ्य क्षमता निर्माण पर जोर दिया।"
    },
    {
        "q_no": 3,
        "question": "The Chola navy was known for its expedition against:",
        "options": ["(A) Cambodia and Laos", "(B) Vietnam", "(C) Indonesia and Sri Lanka", "(D) Maldives"],
        "answer": "C",
        "explanation": "The Chola dynasty under Rajendra Chola I launched naval expeditions against Srivijaya Empire (Indonesia/Malaysia) and Sri Lanka.",
        "narration_q": "Question 3. The Chola navy was known for its expedition against which region?",
        "narration_a": "The correct answer is Option C. Indonesia and Sri Lanka. The Chola dynasty under Rajendra Chola the First launched famous naval expeditions against the Srivijaya Empire, which covered modern Indonesia and Malaysia, as well as Sri Lanka. The Chola navy was one of the most powerful navies in ancient India."
    },
    {
        "q_no": 4,
        "question": "The PM Gati Shakti - National Logistics Policy targets:",
        "options": ["(A) Achieving net-zero carbon emissions in urban transport", "(B) Integrating road, rail, port, and airport infrastructure for faster goods movement", "(C) Promoting bullet train corridors", "(D) Increasing domestic shipbuilding industry"],
        "answer": "B",
        "explanation": "PM Gati Shakti is a master plan for multimodal connectivity integrating all infrastructure on a single digital platform.",
        "narration_q": "Question 4. The PM Gati Shakti National Logistics Policy targets which of the following?",
        "narration_a": "The correct answer is Option B. Integrating road, rail, port, and airport infrastructure for faster goods movement. PM Gati Shakti, launched in October 2021, is a 100 lakh crore rupees national master plan for multimodal connectivity, aiming to reduce logistics costs."
    },
    {
        "q_no": 5,
        "question": "What differentiates India's Long-Term Low Emission Development Strategy (LT-LEDS) from the NAPCC?",
        "options": ["(A) It targets only renewable energy", "(B) It provides sector-specific deep decarbonization roadmaps", "(C) It replaces all earlier missions", "(D) It excludes forestry"],
        "answer": "B",
        "explanation": "LT-LEDS provides sector-specific deep decarbonization roadmaps for long-term net-zero transition by 2070.",
        "narration_q": "Question 5. What differentiates India's Long-Term Low Emission Development Strategy from the N A P C C?",
        "narration_a": "The correct answer is Option B. It provides sector-specific deep decarbonization roadmaps. India's L T LEDS, presented at COP 27 in 2022, provides detailed pathways for energy, industry, transport, and land use sectors, targeting net-zero by 2070."
    },
    {
        "q_no": 6,
        "question": "Mustard Gas is:",
        "options": ["(A) Uranium hexafluoride", "(B) Dichlorodiphenyltrichloroethane", "(C) 2,2'-dichlorodiethylsulfide", "(D) Diethylsulphoxide"],
        "answer": "C",
        "explanation": "Mustard Gas is 2,2'-dichlorodiethylsulfide, a chemical weapon used in WWI, banned under Chemical Weapons Convention.",
        "narration_q": "Question 6. Mustard Gas is chemically known as which of the following?",
        "narration_a": "The correct answer is Option C. 2,2 prime dichlorodiethylsulfide. Mustard Gas is a vesicant or blister agent that was used as a chemical weapon in World War One. It was later banned under the Chemical Weapons Convention of 1993."
    },
    {
        "q_no": 7,
        "question": "Settlement geography statements:\nStatement-1: Humid tropical regions have compact villages.\nStatement-2: Isolated farmsteads in densely populated rice-growing regions.\nStatement-3: Mountains lead to clustered settlements.\nStatement-4: Settlement morphology linked to agriculture.",
        "options": ["(A) 1, 2, 3 correct; 4 incorrect", "(B) 1, 3, 4 correct; 2 incorrect", "(C) 2, 3, 4 correct; 1 incorrect", "(D) Only 3 correct"],
        "answer": "B",
        "explanation": "Statement 2 is incorrect. In densely populated rice-growing areas, compact settlements are common, not isolated farmsteads.",
        "narration_q": "Question 7. Consider the statements about settlement geography. Which combination is correct?",
        "narration_a": "The correct answer is Option B. Statements 1, 3, and 4 are correct while Statement 2 is incorrect. In densely populated rice-growing areas like South and East Asia, compact nucleated settlements are common, not isolated farmsteads. Isolated farmsteads are typical of sparsely populated areas."
    },
    {
        "q_no": 8,
        "question": "The basic foundation of global economic governance in the post-WWII era was laid by:",
        "options": ["a) IMF, World Bank, GATT", "b) IMF, World Bank, Asian Development Bank", "c) World Bank, GATT, BRICS", "d) Asian Development Bank, IMF, IBRD"],
        "answer": "A",
        "explanation": "IMF, World Bank, and GATT formed the post-WWII Bretton Woods economic order.",
        "narration_q": "Question 8. The basic foundation of global economic governance after World War 2 was laid by which combination of institutions?",
        "narration_a": "The correct answer is Option A. I M F, World Bank, and G A T T. These three pillars, established through the Bretton Woods system, formed the foundation of the modern global economic order. I M F handles monetary stability, World Bank handles development, and G A T T, now the W T O, governs international trade."
    },
    {
        "q_no": 9,
        "question": "Inflation in India:\n1. CPI is primary metric for RBI monetary policy.\n2. Core inflation excludes food and fuel.\n3. Supply-side factors affect agricultural prices.\n4. Headline inflation includes volatile components.",
        "options": ["(A) 1, 2 and 3 only", "(B) 1, 3 and 4 only", "(C) 2, 3 and 4 only", "(D) All of the above"],
        "answer": "D",
        "explanation": "All four statements about inflation in India are correct.",
        "narration_q": "Question 9. Consider the statements about inflation in India. Which are correct?",
        "narration_a": "The correct answer is Option D. All of the above. All four statements are correct. RBI uses CPI for inflation targeting with a 4 percent target. Core inflation excludes volatile food and fuel. Monsoons and global oil prices are supply-side drivers. And headline inflation includes all components including food and energy."
    },
    {
        "q_no": 10,
        "question": "A Committee to formulate fundamental duties after emergency in 1976 was headed by:",
        "options": ["(A) VC Shukla", "(B) DK Barooah", "(C) Sardar Swaran Singh", "(D) Sanjeeva Reddy"],
        "answer": "C",
        "explanation": "Sardar Swaran Singh Committee recommended Fundamental Duties, added by 42nd Amendment Act 1976.",
        "narration_q": "Question 10. The committee constituted to formulate fundamental duties after the emergency in 1976 was headed by whom?",
        "narration_a": "The correct answer is Option C. Sardar Swaran Singh. The Sardar Swaran Singh Committee of 1976 recommended adding Fundamental Duties to the Constitution. Based on this, the 42nd Amendment Act added Part 4A with Article 51A, listing 10 fundamental duties."
    },
    {
        "q_no": 11,
        "question": "Wave-like character of an electron is proved by:",
        "options": ["(A) Ionization of an atom", "(B) Flow of electrons in a metal wire", "(C) Deflection of electron beam by electrical plates", "(D) Diffraction pattern of electrons from a crystalline solid"],
        "answer": "D",
        "explanation": "Davisson-Germer experiment proved wave nature of electrons through diffraction from nickel crystal.",
        "narration_q": "Question 11. The wave-like character of an electron is proved by which phenomenon?",
        "narration_a": "The correct answer is Option D. The diffraction pattern of electrons scattered from a crystalline solid. This was proved by the Davisson Germer experiment in 1927, where electrons scattered off a nickel crystal showed a diffraction pattern, confirming de Broglie's wave-particle duality hypothesis."
    },
    {
        "q_no": 12,
        "question": "Match Nationalist Women with Activities:\na) Sarojini Naidu b) Usha Mehta c) Aruna Asaf Ali d) Dr. Lakshmi Swaminathan",
        "options": ["(A) 4 2 1 3", "(B) 3 4 1 2", "(C) 4 3 2 1", "(D) 3 2 4 1"],
        "answer": "B",
        "explanation": "Sarojini Naidu led Dharsana Satyagraha, Usha Mehta operated secret radio, Aruna Asaf Ali was underground leader, Dr. Lakshmi joined INA.",
        "narration_q": "Question 12. Match the nationalist women with their activities. Sarojini Naidu, Usha Mehta, Aruna Asaf Ali, and Dr. Lakshmi Swaminathan.",
        "narration_a": "The correct answer is Option B, giving the order 3, 4, 1, 2. Sarojini Naidu led the Salt Satyagraha at Dharsana. Usha Mehta operated the secret Congress Radio during Quit India movement. Aruna Asaf Ali was the famous underground movement leader. And Dr. Lakshmi Swaminathan joined Subhas Bose's I N A."
    },
    {
        "q_no": 13,
        "question": "The 2025 Cambodia-Thailand border conflict was primarily triggered by:",
        "options": ["(A) Oil and gas disputes", "(B) Historical disputes over Preah Vihear Temple", "(C) Mekong River water-sharing", "(D) Trade War"],
        "answer": "B",
        "explanation": "The conflict centers on the Preah Vihear Temple, a UNESCO World Heritage Site on the border.",
        "narration_q": "Question 13. The 2025 Cambodia Thailand border conflict was primarily triggered by what?",
        "narration_a": "The correct answer is Option B. Historical disputes over the Preah Vihear Temple and surrounding territory. The International Court of Justice ruled in 1962 that the temple belongs to Cambodia, but the surrounding area remained contested. The temple is a UNESCO World Heritage Site situated on a cliff on the border."
    },
    {
        "q_no": 14,
        "question": "The term 'seamless web' about the Indian Constitution was used by:",
        "options": ["(A) Granville Austin", "(B) K.C. Wheare", "(C) Donald Smith", "(D) A.V. Dicey"],
        "answer": "A",
        "explanation": "Granville Austin described the Indian Constitution as a 'seamless web' in his famous book.",
        "narration_q": "Question 14. The term seamless web, with reference to the interconnectedness of different parts of the Indian Constitution, was used by which author?",
        "narration_a": "The correct answer is Option A. Granville Austin. In his landmark book, The Indian Constitution: Cornerstone of a Nation, published in 1966, he described the Constitution as a seamless web where social revolution, democratic government, and national unity are interwoven inseparably."
    },
    {
        "q_no": 15,
        "question": "Which combinations are correct about social welfare policies and their year?\na) PM POSHAN: 2021 b) Right to Education: 2009 c) Ayushman Bharat: 2018 d) PM Awaas Yojana: 2015",
        "options": ["(A) a, b, c and d", "(B) c, a, d and b", "(C) b, d, c and a", "(D) d, c, a and b"],
        "answer": "A",
        "explanation": "All four policies are correctly matched with their years.",
        "narration_q": "Question 15. Which combinations are correct regarding social welfare policies and the year they were introduced?",
        "narration_a": "The correct answer is Option A. All four are correctly matched. PM POSHAN was renamed in 2021, Right to Education Act was passed in 2009, Ayushman Bharat was launched in September 2018, and PM Awaas Yojana was launched in June 2015."
    },
    {
        "q_no": 16,
        "question": "Urbanization challenges in India:\n1. Rapid urbanization strains infrastructure\n2. Slums grow due to unaffordable housing\n3. Urban areas have higher unemployment than rural\n4. Smart Cities Mission promotes sustainable cities",
        "options": ["(A) 1, 2 and 3 only", "(B) 1, 3 and 4 only", "(C) 1, 2 and 4 only", "(D) 2, 3 and 4 only"],
        "answer": "C",
        "explanation": "Statement 3 is incorrect - urban areas generally have LOWER unemployment than rural areas.",
        "narration_q": "Question 16. Consider the statements about challenges of urbanization in India. Which are correct?",
        "narration_a": "The correct answer is Option C. Statements 1, 2, and 4 are correct. Statement 3 is incorrect because urban areas generally have lower unemployment rates than rural areas, not higher. Urban areas offer more diverse job opportunities."
    },
    {
        "q_no": 17,
        "question": "Who was the founder of the Lingayat sect?",
        "options": ["(A) Appar", "(B) Basava", "(C) Bijjala", "(D) Abhinava"],
        "answer": "B",
        "explanation": "Basaveshwara founded the Lingayat movement in 12th century Karnataka.",
        "narration_q": "Question 17. Who was the founder of the Lingayat sect?",
        "narration_a": "The correct answer is Option B. Basava, also known as Basaveshwara. He founded the Lingayat or Virashaiva movement in the 12th century in Karnataka. He promoted social equality, rejected the caste system, and established the Anubhava Mantapa, considered the world's first parliament of mystics."
    },
    {
        "q_no": 18,
        "question": "Tarkunde Report is related to:",
        "options": ["(A) Electoral Reforms", "(B) Centre State Relations", "(C) Economic Reforms", "(D) Educational Reforms"],
        "answer": "A",
        "explanation": "Tarkunde Committee studied electoral reforms in India.",
        "narration_q": "Question 18. The Tarkunde Report is related to which of the following?",
        "narration_a": "The correct answer is Option A. Electoral Reforms. The Tarkunde Committee, headed by Justice V M Tarkunde in 1974-75, recommended state funding of elections and reduction of voting age from 21 to 18 years."
    },
    {
        "q_no": 19,
        "question": "CAMPA funds are prioritized for:",
        "options": ["(A) Mining clearance proposals", "(B) Community-managed wind farms", "(C) Compensatory afforestation and eco-restoration", "(D) River-interlinking evaluations"],
        "answer": "C",
        "explanation": "CAMPA funds are for compensatory afforestation when forest land is diverted for non-forest use.",
        "narration_q": "Question 19. The CAMPA funds are prioritized for which activities?",
        "narration_a": "The correct answer is Option C. Compensatory afforestation and eco-restoration. CAMPA, the Compensatory Afforestation Fund Management and Planning Authority, manages funds collected when forest land is diverted for non-forest purposes. The CAMPA Act 2016 governs these funds."
    },
    {
        "q_no": 20,
        "question": "The Dyarchical system was introduced by:",
        "options": ["(A) Government of India Act, 1909", "(B) Government of India Resolution 1918", "(C) Government of India Act, 1919", "(D) Government of India Act, 1935"],
        "answer": "C",
        "explanation": "GoI Act 1919 (Montagu-Chelmsford Reforms) introduced Dyarchy at provincial level.",
        "narration_q": "Question 20. The Dyarchical system of government was introduced by which measure?",
        "narration_a": "The correct answer is Option C. The Government of India Act 1919, also known as the Montagu Chelmsford Reforms. Under Dyarchy, provincial subjects were divided into Transferred subjects under Indian ministers and Reserved subjects under the Governor."
    },
    {
        "q_no": 21,
        "question": "Which is a non-reducing sugar?",
        "options": ["(A) Glucose", "(B) Maltose", "(C) Sucrose", "(D) Fructose"],
        "answer": "C",
        "explanation": "Sucrose has no free anomeric carbon, making it a non-reducing sugar.",
        "narration_q": "Question 21. Which of the following is a non-reducing sugar?",
        "narration_a": "The correct answer is Option C. Sucrose. Sucrose is a non-reducing sugar because both the anomeric carbons of glucose and fructose are involved in the glycosidic bond, leaving no free anomeric carbon. Glucose, fructose, and maltose are all reducing sugars."
    },
    {
        "q_no": 22,
        "question": "Which statements about World Cultural Realms are NOT correct?",
        "options": ["(A) 1 and 3 only", "(B) 2 and 4 only", "(C) 3 only", "(D) 1, 3 and 5"],
        "answer": "C",
        "explanation": "Statement 3 is wrong - Islamic Realm extends far beyond the Arabian Peninsula.",
        "narration_q": "Question 22. Which statements about World Cultural Realms are NOT correct?",
        "narration_a": "The correct answer is Option C. Only statement 3 is incorrect. The Islamic Realm is not restricted solely to the Arabian Peninsula. It extends across North Africa, Central Asia, South Asia, and Southeast Asia, including countries like Indonesia and Malaysia."
    },
    {
        "q_no": 23,
        "question": "Which statements about CM-KISAN scheme of Odisha are NOT correct?",
        "options": ["(A) 1 only", "(B) 1 and 2 only", "(C) 2 and 3 only", "(D) 1 and 4 only"],
        "answer": "A",
        "explanation": "Statement 1 is wrong - CM-KISAN is for ALL farmers, not exclusively large landholders.",
        "narration_q": "Question 23. Which statements about the C M KISAN scheme of Odisha are NOT correct?",
        "narration_a": "The correct answer is Option A. Only statement 1 is incorrect. CM KISAN is designed for all farmers including small and marginal farmers, not exclusively for large landholding farmers. It is a progressive and inclusive scheme."
    },
    {
        "q_no": 24,
        "question": "Arrange committees in chronological order:\na) N.N. Vohra b) Rajinder Sachar c) D.S. Kothari d) Raja J. Chelliah",
        "options": ["(A) a, b, c and d", "(B) c, d, a and b", "(C) b, a, c and d", "(D) a, c, b and d"],
        "answer": "D",
        "explanation": "Chronological order: Kothari (1964), Chelliah (1991), Vohra (1993), Sachar (2005).",
        "narration_q": "Question 24. Arrange the following committees in chronological order.",
        "narration_a": "The correct answer is Option D. The chronological order is: D S Kothari Committee in 1964 for education reforms, Raja Chelliah Committee in 1991 for tax reforms, N N Vohra Committee in 1993 on criminalization of politics, and Rajinder Sachar Committee in 2005 on the status of the Muslim community."
    },
    {
        "q_no": 25,
        "question": "Which is not a dye?",
        "options": ["(A) Alizarin", "(B) Fluorescein", "(C) Phenolphthalein", "(D) Anthranilic acid"],
        "answer": "D",
        "explanation": "Anthranilic acid is an amino acid derivative used in pharmaceutical synthesis, not a dye.",
        "narration_q": "Question 25. Which of the following is not a dye?",
        "narration_a": "The correct answer is Option D. Anthranilic acid. It is an amino acid derivative used in pharmaceutical synthesis, not a dye. Alizarin is a red dye, Fluorescein is a fluorescent dye, and Phenolphthalein is used as an indicator."
    },
    {
        "q_no": 26,
        "question": "About IDCO - which statement is NOT correct?",
        "options": ["(A) 2 only", "(B) 4 only", "(C) 1 and 3 only", "(D) 3 and 5 only"],
        "answer": "B",
        "explanation": "Statement 4 is wrong - IDCO does include land acquisition and land bank creation.",
        "narration_q": "Question 26. Consider the statements about Odisha Industrial Infrastructure Development Corporation. Which is NOT correct?",
        "narration_a": "The correct answer is Option B. Statement 4 is not correct. IDCO's functions do include land acquisition and creation of land banks for major industrial projects. IDCO, established in 1981, is the nodal agency for providing industrial infrastructure and land in Odisha."
    },
    {
        "q_no": 27,
        "question": "Statements about the CAG - choose the correct answer:",
        "options": ["(A) a and b", "(B) a and c", "(C) b and d", "(D) a, b, c and d"],
        "answer": "D",
        "explanation": "All statements about the CAG are correct.",
        "narration_q": "Question 27. Consider the statements about the Comptroller and Auditor General. Which are correct?",
        "narration_a": "The correct answer is Option D. All four statements are correct. The CAG office was modelled on the Auditor General under the Government of India Act 1919. CAG is the impartial head of India's audit system under Article 148. CAG can be removed for proven misbehaviour. And the term is 6 years or until age 65."
    },
    {
        "q_no": 28,
        "question": "Under which Mughal Emperor was the Muhtasib office instituted in Odisha?",
        "options": ["(A) Shahjahan", "(B) Aurangzeb", "(C) Jahangir", "(D) Humayun"],
        "answer": "B",
        "explanation": "Aurangzeb appointed Muhtasibs to enforce Islamic law across the empire including Odisha.",
        "narration_q": "Question 28. Under which Mughal Emperor was the office of Muhtasib, or Censor of Public Morals, instituted in Odisha?",
        "narration_a": "The correct answer is Option B. Aurangzeb. He appointed Muhtasibs, or censors of public morals, across the Mughal Empire including in Odisha. Aurangzeb was known for his strict religious policies, including reimposing the Jizya tax."
    },
    {
        "q_no": 29,
        "question": "First Leader to move resolution for unification of Odia speaking tracts:",
        "options": ["(A) Madhusudan Das", "(B) Gopa bandhu Das", "(C) Hare Krushna Mahatab", "(D) Nil Kantha Das"],
        "answer": "A",
        "explanation": "Madhusudan Das was the first to demand unification of Odia-speaking areas.",
        "narration_q": "Question 29. Who was the first leader to move a resolution in the Central Legislative Assembly demanding unification of all Odia speaking tracts?",
        "narration_a": "The correct answer is Option A. Madhusudan Das, known as Utkal Gaurav or the Grand Old Man of Odisha. He pioneered the Odia linguistic identity movement. Odisha became a separate province on April 1st, 1936."
    },
    {
        "q_no": 30,
        "question": "Statements about Inter-State Council:",
        "options": ["(A) 1 and 4", "(B) 1, 3 and 4", "(C) 2, 3 and 1", "(D) 1, 2 and 3"],
        "answer": "A",
        "explanation": "Only statements 1 and 4 are correct. PM is Chairman, not Home Minister. Sarkaria recommended it, not Punchhi.",
        "narration_q": "Question 30. Consider the statements about the Inter-State Council. Which are correct?",
        "narration_a": "The correct answer is Option A. Only statements 1 and 4 are correct. The Inter-State Council is established under Article 263 and discusses matters of common interest. Statement 2 is wrong because the Sarkaria Commission, not Punchhi, recommended it. Statement 3 is wrong because the Prime Minister, not the Home Minister, is the Chairman."
    },
    {
        "q_no": 31,
        "question": "Which climate initiative supports Himalayan glacial monitoring?",
        "options": ["(A) ICAP", "(B) National Mission on Sustaining the Himalayan Ecosystem", "(C) State REDD+ Programme", "(D) Bharat Clean Energy Mission"],
        "answer": "B",
        "explanation": "NMSHE under NAPCC specifically focuses on monitoring Himalayan glaciers.",
        "narration_q": "Question 31. Which climate initiative specifically supports Himalayan glacial monitoring?",
        "narration_a": "The correct answer is Option B. The National Mission on Sustaining the Himalayan Ecosystem. It is one of the 8 missions under the National Action Plan on Climate Change, specifically focusing on monitoring Himalayan glaciers, biodiversity conservation, and understanding climate impacts."
    },
    {
        "q_no": 32,
        "question": "Which statements about global industrial patterns are NOT correct?",
        "options": ["(A) 2 and 3 only", "(B) 1 and 2 only", "(C) 3 and 1 only", "(D) 4 only"],
        "answer": "D",
        "explanation": "Statement 4 is wrong - Canada and Australia are resource-based, not heavy industry based.",
        "narration_q": "Question 32. Which statements about the global industrial pattern are NOT correct?",
        "narration_a": "The correct answer is Option D. Only statement 4 is incorrect. Canada and Australia are primarily known for resource-based industries like mining, agriculture, and forestry, not for heavy industry. They are major exporters of natural resources."
    },
    {
        "q_no": 33,
        "question": "First major administrative measure by Congress Ministry in Odisha on 23 April 1946:",
        "options": ["(A) Abolition of Zamindari Settlements", "(B) Release of political prisoners", "(C) Repeal of salt laws", "(D) Introduction of Compulsory primary education"],
        "answer": "A",
        "explanation": "Abolition of Zamindari settlements was the first major measure under Hare Krushna Mahatab.",
        "narration_q": "Question 33. What was the first major administrative measure by the Congress Ministry in Odisha on 23rd April 1946?",
        "narration_a": "The correct answer is Option A. Abolition of Zamindari Settlements. The Congress Ministry under Hare Krushna Mahatab took this landmark land reform measure to free peasants from the exploitative zamindari system."
    },
    {
        "q_no": 34,
        "question": "Which best defines Pareto Optimality?",
        "options": ["(A) Everyone equally well-off", "(B) No one can be better off without making someone worse off", "(C) Total wealth maximized", "(D) Government redistributes equally"],
        "answer": "B",
        "explanation": "Pareto Optimality means no further improvements possible without making someone worse off.",
        "narration_q": "Question 34. Which of the following best defines the concept of Pareto Optimality?",
        "narration_a": "The correct answer is Option B. A situation where no one can be made better off without making someone else worse off. Named after Italian economist Vilfredo Pareto, this is a key concept in welfare economics. It doesn't mean equality or maximum wealth, just that no further win-win improvements are possible."
    },
    {
        "q_no": 35,
        "question": "Statements about impeachment of Supreme Court Judge - which are INCORRECT?",
        "options": ["(A) a and b", "(B) c only", "(C) c and d", "(D) a, c and d"],
        "answer": "C",
        "explanation": "Statements c and d are incorrect - regarding MP requirements and President's pardon power.",
        "narration_q": "Question 35. Consider statements about impeachment of a Supreme Court Judge. Which are incorrect?",
        "narration_a": "The correct answer is Option C. Statements c and d are incorrect. The President cannot pardon a judge, as removal is by Parliament's address only. Also, the specific number of MPs required needs correction. Statements a and b about Article 124(4) and the grounds for impeachment are correct."
    },
    {
        "q_no": 36,
        "question": "Statements about SDGs - which are correct?",
        "options": ["(A) 1, 2 and 3 only", "(B) 1, 3 and 4 only", "(C) 2, 3 and 4 only", "(D) All of the above"],
        "answer": "A",
        "explanation": "Statement 4 is wrong - SCP is under SDG 12, not SDG 14.",
        "narration_q": "Question 36. Consider the statements about Sustainable Development Goals. Which are correct?",
        "narration_a": "The correct answer is Option A. Statements 1, 2, and 3 only. Statement 4 is incorrect because Sustainable Consumption and Production is under SDG 12, not SDG 14. SDG 14 is about Life Below Water, which deals with ocean conservation."
    },
    {
        "q_no": 37,
        "question": "Section 4 of RTI Act - publish information within ___ days:",
        "options": ["(A) 120", "(B) 30", "(C) 110", "(D) 10"],
        "answer": "A",
        "explanation": "Section 4 mandates proactive disclosure of 17 categories within 120 days.",
        "narration_q": "Question 37. Section 4 of the R T I Act states that public authorities must publish information within how many days?",
        "narration_a": "The correct answer is Option A. 120 days. Section 4 of the Right to Information Act 2005 mandates that every public authority shall proactively publish 17 categories of information within 120 days of enactment."
    },
    {
        "q_no": 38,
        "question": "Statements about Ramsar sites in India:",
        "options": ["(A) 1 and 2 only", "(B) 2 and 3 only", "(C) 1 and 3 only", "(D) 1, 2 and 3"],
        "answer": "D",
        "explanation": "All three statements about Ramsar sites are correct, including Chilika Lake being the first.",
        "narration_q": "Question 38. Consider the statements about Ramsar sites in India. Which are correct?",
        "narration_a": "The correct answer is Option D. All three statements are correct. Ramsar sites are declared based on ecological importance. Chilika Lake in Odisha was one of India's first two Ramsar sites designated in 1981. And as of 2023, India has more than 75 Ramsar sites."
    },
    {
        "q_no": 39,
        "question": "The writ of Mandamus is issued:",
        "options": ["(A) To release from illegal detention", "(B) To transfer a case", "(C) To compel a public official to perform duty", "(D) To question holding of public office"],
        "answer": "C",
        "explanation": "Mandamus compels performance of a mandatory public duty.",
        "narration_q": "Question 39. The writ of Mandamus is issued for what purpose?",
        "narration_a": "The correct answer is Option C. To compel a public official to perform a public duty. Mandamus, meaning we command, orders a government official to fulfill a legal obligation. Remember: Habeas Corpus is for illegal detention, Certiorari for case transfer, and Quo Warranto to question authority."
    },
    {
        "q_no": 40,
        "question": "Statements about Samudrayaan Mission:",
        "options": ["(A) 1 only", "(B) 2 and 3", "(C) 1 and 4 only", "(D) 4 only"],
        "answer": "B",
        "explanation": "Samudrayaan develops MATSYA 6000 submersible for 6000m depth ocean exploration.",
        "narration_q": "Question 40. Consider the statements about the Samudrayaan Mission. Which are correct?",
        "narration_a": "The correct answer is Option B. Statements 2 and 3 are correct. Samudrayaan aims to develop MATSYA 6000, a self-propelled manned submersible that can reach 6000 meters depth. It's part of the Deep Ocean Mission for mineral exploration, not for nuclear submarines or marine tourism."
    },
    {
        "q_no": 41,
        "question": "India's aquaculture policies - which are correct?",
        "options": ["(A) 1, 2 and 3 only", "(B) 1 and 4 only", "(C) 2 and 4 only", "(D) 1, 3 and 4 only"],
        "answer": "A",
        "explanation": "FAO's Code of Conduct is voluntary, not legally binding, making statement 4 incorrect.",
        "narration_q": "Question 41. Which statements about India's aquaculture policies are correct?",
        "narration_a": "The correct answer is Option A. Statements 1, 2, and 3 only. Statement 4 is incorrect because the F A O's Code of Conduct for Responsible Fisheries is voluntary, not legally binding. PMMSY boosts fish production, Coastal Aquaculture Authority regulates brackish water, and NFDB promotes modern practices."
    },
    {
        "q_no": 42,
        "question": "Time limit for POSH Act 2013 complaint:",
        "options": ["(A) 14 days", "(B) One month", "(C) Two months", "(D) Three months"],
        "answer": "D",
        "explanation": "The complaint must be filed within 3 months, extendable by another 3 months.",
        "narration_q": "Question 42. What is the time limit for making a complaint under the POSH Act 2013?",
        "narration_a": "The correct answer is Option D. Three months. Under the Prevention of Sexual Harassment at Workplace Act, the aggrieved woman must file a complaint within 3 months of the incident, which can be extended by another 3 months. The inquiry must be completed within 90 days."
    },
    {
        "q_no": 43,
        "question": "Statements about endemic species in India:",
        "options": ["(A) 1 and 2 only", "(B) 2 and 3 only", "(C) 1 and 3 only", "(D) 1, 2 and 3"],
        "answer": "A",
        "explanation": "Statement 3 is wrong - endemic species are not always Critically Endangered.",
        "narration_q": "Question 43. Consider the statements about endemic species in India. Which are correct?",
        "narration_a": "The correct answer is Option A. Statements 1 and 2 only. Statement 3 is incorrect because endemic species are not always critically endangered. Endemism means geographic restriction, which is different from conservation status. The Nilgiri Tahr is indeed endemic to the Western Ghats."
    },
    {
        "q_no": 44,
        "question": "UPSC is mentioned in which Part of the Constitution?",
        "options": ["(A) Part VII", "(B) Part XIII", "(C) Part XIV", "(D) Part IX"],
        "answer": "C",
        "explanation": "UPSC is in Part XIV (Services Under the Union and States), Articles 315-323.",
        "narration_q": "Question 44. The Union Public Service Commission is mentioned in which part of the Indian Constitution?",
        "narration_a": "The correct answer is Option C. Part 14, which deals with Services Under the Union and the States, covering Articles 315 to 323. Part 14 deals with Public Service Commissions at both Union and State levels."
    },
    {
        "q_no": 45,
        "question": "Statements about delimitation in India:",
        "options": ["(A) 1, 2 and 3 only", "(B) 1, 3 and 4 only", "(C) 2, 3 and 4 only", "(D) All of the above"],
        "answer": "D",
        "explanation": "All four statements about delimitation are correct.",
        "narration_q": "Question 45. Consider the statements about delimitation in India. Which are correct?",
        "narration_a": "The correct answer is Option D. All of the above. All four statements are correct. Delimitation redraws constituency boundaries, its orders cannot be challenged in court, it upholds the one person one vote principle, and the current exercise is based on the 2001 Census."
    },
    {
        "q_no": 46,
        "question": "Which British Governor-General annexed Odisha?",
        "options": ["(A) Warren Hastings", "(B) Lord Cornwallis", "(C) Lord Wellesley", "(D) Lord Dalhousie"],
        "answer": "C",
        "explanation": "Lord Wellesley annexed Odisha in 1803 after the Anglo-Maratha War.",
        "narration_q": "Question 46. Which British Governor General formally annexed Odisha into the British Empire?",
        "narration_a": "The correct answer is Option C. Lord Wellesley. He annexed Odisha in 1803 after the Anglo-Maratha War. The Treaty of Deogaon forced the Bhonsle ruler to cede Cuttack, which included most of Odisha, to the British."
    },
    {
        "q_no": 47,
        "question": "Which Nobel Prize 2024 match is wrong?",
        "options": ["(A) Peace - Narges Mohammadi", "(B) Literature - Han Kang", "(C) Economics - Daron Acemoglu et al.", "(D) Physics - John Hopfield & Geoffrey Hinton"],
        "answer": "A",
        "explanation": "Narges Mohammadi won Nobel Peace Prize in 2023, not 2024. 2024 Peace went to Nihon Hidankyo.",
        "narration_q": "Question 47. Which Nobel Prize category does not match properly with its 2024 laureate?",
        "narration_a": "The correct answer is Option A. Narges Mohammadi won the Nobel Peace Prize in 2023, not 2024. The 2024 Nobel Peace Prize was awarded to Nihon Hidankyo, a Japanese organization of atomic bomb survivors. All other options correctly list 2024 laureates."
    },
    {
        "q_no": 48,
        "question": "First Black man to win Oscar for Best Costume Design at 97th Academy Awards:",
        "options": ["(A) Paul Tazewell", "(B) Olivier Persin", "(C) Emilia Perez", "(D) Sean Baker"],
        "answer": "A",
        "explanation": "Paul Tazewell won for the film 'Wicked' at the 97th Oscars.",
        "narration_q": "Question 48. Who made history as the first Black man to win the Oscar for Best Costume Design at the 97th Academy Awards?",
        "narration_a": "The correct answer is Option A. Paul Tazewell. He won for his work on the film Wicked at the 97th Academy Awards in 2025. He is also known for his Tony Award winning costume design for the Broadway musical Hamilton."
    },
    {
        "q_no": 49,
        "question": "Arrange texts in chronological order:\na) Brihalaranyaka Upanishad b) Manusmriti c) Arthashastra d) Milinda Panha",
        "options": ["(A) a-b-c-d", "(B) b-c-a-d", "(C) c-a-b-d", "(D) a-c-b-d"],
        "answer": "A",
        "explanation": "Order: Brihalaranyaka Upanishad (800 BCE), Manusmriti, Arthashastra, Milinda Panha.",
        "narration_q": "Question 49. Arrange the following ancient texts in their chronological order of composition.",
        "narration_a": "The correct answer is Option A. The chronological order is: Brihalaranyaka Upanishad from around 800 to 600 BCE, then Manusmriti, then Arthashastra, and finally Milinda Panha. This sequence represents a span of several centuries of Indian intellectual tradition."
    },
    {
        "q_no": 50,
        "question": "Statements about India's NDCs:",
        "options": ["(A) 1 and 2 only", "(B) 2 and 3 only", "(C) 1 and 3 only", "(D) 1, 2 and 3"],
        "answer": "D",
        "explanation": "All three statements about India's Nationally Determined Contributions are correct.",
        "narration_q": "Question 50. Consider the statements about India's Nationally Determined Contributions. Which are correct?",
        "narration_a": "The correct answer is Option D. All three statements are correct. India targets 45 percent reduction in emissions intensity by 2030, aims for 50 percent non-fossil fuel capacity by 2030, and these targets are based on Prime Minister Modi's Panchamrit pledge at COP 26 in Glasgow."
    },
    {
        "q_no": 51,
        "question": "India's new Deputy National Security Adviser as of August 2025:",
        "options": ["(A) Rajinder Khanna", "(B) T.V. Ravichandran", "(C) Anish Dayal Singh", "(D) Pankaj Kumar Singh"],
        "answer": "B",
        "explanation": "T.V. Ravichandran was appointed Deputy NSA in August 2025.",
        "narration_q": "Question 51. Who was appointed as India's new Deputy National Security Adviser as of August 2025?",
        "narration_a": "The correct answer is Option B. T V Ravichandran. He was appointed as India's new Deputy National Security Adviser in August 2025, working under the National Security Adviser in coordinating national security affairs."
    },
    {
        "q_no": 52,
        "question": "Match UN Days with dates:\n3 March, 7 April, 3 May, 20 June",
        "options": ["(A) a-1 b-2 c-3 d-4", "(B) a-2 b-3 c-4 d-1", "(C) a-1 b-3 c-4 d-2", "(D) a-3 b-2 c-1 d-4"],
        "answer": "A",
        "explanation": "3 March=Wildlife Day, 7 April=Health Day, 3 May=Press Freedom Day, 20 June=Refugee Day.",
        "narration_q": "Question 52. Match the United Nations observance days with their correct dates.",
        "narration_a": "The correct answer is Option A. March 3 is World Wildlife Day, April 7 is World Health Day, May 3 is World Press Freedom Day, and June 20 is World Refugee Day. These are frequently asked in competitive examinations."
    },
    {
        "q_no": 53,
        "question": "Official theme of the 38th National Games?",
        "options": ["(A) Fit India", "(B) Sustainable Olympics", "(C) Green Games", "(D) Eco-Sports Initiative"],
        "answer": "C",
        "explanation": "38th National Games (Uttarakhand, 2025) had 'Green Games' as theme.",
        "narration_q": "Question 53. What was the official theme of the 38th National Games?",
        "narration_a": "The correct answer is Option C. Green Games. The 38th National Games, held in Uttarakhand in 2025, adopted Green Games as its official theme, emphasizing environmental sustainability in sports events."
    },
    {
        "q_no": 54,
        "question": "Match Colonial Policies with Impact on Odisha:",
        "options": ["(A) a-1, b-2, c-3, d-4, e-5", "(B) a-2, b-1, c-3, d-4, e-5", "(C) a-4, b-5, c-1, d-3, e-2", "(D) a-5, b-3, c-4, d-2, e-1"],
        "answer": "A",
        "explanation": "Permanent Settlement caused economic distress, British reorganization split Odia tracts.",
        "narration_q": "Question 54. Match the colonial policies with their impact on Odisha.",
        "narration_a": "The correct answer is Option A. The Permanent Settlement of 1793 aggravated economic distress. British reorganization split Odia speaking tracts under different presidencies. Bengali imposition fueled the Odia linguistic identity movement. And the Simon Commission was petitioned by Krushna Chandra Gajapati for a separate province."
    },
    {
        "q_no": 55,
        "question": "Match Indian Rivers with Tributaries:",
        "options": ["(A) 2 1 3 4", "(B) 3 2 1 4", "(C) 4 3 2 1", "(D) 1 4 3 2"],
        "answer": "B",
        "explanation": "Chambal-Banas, Cauvery-Noyyal, Krishna-Bhima, Godavari-Manjra.",
        "narration_q": "Question 55. Match the Indian Rivers with their correct tributaries: Chambal, Cauvery, Krishna, and Godavari.",
        "narration_a": "The correct answer is Option B, giving the order 3, 2, 1, 4. Chambal's tributary is Banas, Cauvery's is Noyyal, Krishna's major tributary is Bhima, and Godavari's tributary is Manjra."
    },
    {
        "q_no": 56,
        "question": "Match Rivers of Odisha with Tributaries:",
        "options": ["(A) 2 1 3 4", "(B) 3 2 1 4", "(C) 3 1 4 2", "(D) 3 1 2 1"],
        "answer": "C",
        "explanation": "Mahanadi-Ong, Brahmani-Sankha, Baitarani-Deo, Subarnarekha-Raru.",
        "narration_q": "Question 56. Match the rivers of Odisha with their tributaries: Mahanadi, Brahmani, Baitarani, and Subarnarekha.",
        "narration_a": "The correct answer is Option C. Mahanadi's tributary is Ong. Brahmani is formed by the confluence of Sankha and South Koel. Baitarani's tributary is Deo. And Subarnarekha's tributary is Raru."
    },
    {
        "q_no": 57,
        "question": "First to issue gold coins in India?",
        "options": ["(A) Kushans", "(B) Sakas", "(C) Parthians", "(D) Indo Greeks"],
        "answer": "D",
        "explanation": "Indo-Greeks were the first to issue gold coins in India around 2nd century BCE.",
        "narration_q": "Question 57. Who were the first to issue gold coins in India?",
        "narration_a": "The correct answer is Option D. The Indo Greeks. They were the first to issue gold coins in India around the 2nd century BCE. While the Kushans, especially Kanishka, later issued famous gold coins, the Indo Greeks pioneered gold coinage in the Indian subcontinent."
    },
    {
        "q_no": 58,
        "question": "DoSJE signed MoU with which organisation?",
        "options": ["(A) Ministry of Defence", "(B) NHRC", "(C) NALSA", "(D) Central Vigilance Commission"],
        "answer": "C",
        "explanation": "DoSJE signed MoU with NALSA for awareness about social justice schemes.",
        "narration_q": "Question 58. The Department of Social Justice and Empowerment signed an MoU with which organization?",
        "narration_a": "The correct answer is Option C. National Legal Services Authority, or NALSA. The MoU aims to enhance public awareness about social justice schemes for marginalized communities. NALSA provides free legal services to the underprivileged."
    },
    {
        "q_no": 59,
        "question": "Match initiative with year of launch:",
        "options": ["(A) a-2, b-3, c-1, d-4", "(B) a-4, b-1, c-2, d-3", "(C) a-3, b-2, c-4, d-1", "(D) a-1, b-4, c-3, d-2"],
        "answer": "A",
        "explanation": "Ayushman Bharat-2018, National Skill-2015, MGNREGS-2006, PMJDY-2014.",
        "narration_q": "Question 59. Match the government initiatives with their year of launch.",
        "narration_a": "The correct answer is Option A. Ayushman Bharat was launched in 2018. National Skill Development Mission in 2015. MGNREGS in 2006. And Pradhan Mantri Jan Dhan Yojana in 2014."
    },
    {
        "q_no": 60,
        "question": "Match Rajput rulers with battles/events:",
        "options": ["(A) a-2, b-1, c-3, d-4", "(B) a-1, b-3, c-2, d-4", "(C) a-3, b-2, c-4, d-1", "(D) a-4, b-2, c-1, d-3"],
        "answer": "A",
        "explanation": "Rana Sanga-Khanwa, Maharana Pratap-Haldighati, Rao Chandra Sen-vs Akbar, Raja Man Singh-Odisha.",
        "narration_q": "Question 60. Match the Rajput rulers with their notable battles or events.",
        "narration_a": "The correct answer is Option A. Rana Sanga fought the Battle of Khanwa against Babur in 1527. Maharana Pratap fought the Battle of Haldighati against Akbar's forces in 1576. Rao Chandra Sen resisted Akbar's authority. And Raja Man Singh, Akbar's general, conquered Odisha."
    },
    {
        "q_no": 61,
        "question": "Structural transformation of Indian economy:",
        "options": ["(A) 1, 2 and 3 only", "(B) 1, 3 and 4 only", "(C) 2, 3 and 4 only", "(D) All of the above"],
        "answer": "D",
        "explanation": "All four statements are correct about India's economic transformation.",
        "narration_q": "Question 61. Consider the statements about structural transformation of the Indian economy. Which are correct?",
        "narration_a": "The correct answer is Option D. All of the above. All four statements are correct. The services sector drives GDP growth since liberalization. Make in India targets 25 percent manufacturing share. Agriculture's GDP share has declined but employment share remains significant. And premature deindustrialization accurately describes India's development path."
    },
    {
        "q_no": 62,
        "question": "Which Article says SC law is binding on all courts?",
        "options": ["(A) Article 131", "(B) Article 141", "(C) Article 144", "(D) Article 145"],
        "answer": "B",
        "explanation": "Article 141 - law declared by SC shall be binding on all courts in India.",
        "narration_q": "Question 62. Which Article of the Indian Constitution provides that law declared by the Supreme Court shall be binding on all courts?",
        "narration_a": "The correct answer is Option B. Article 141. It states that the law declared by the Supreme Court shall be binding on all courts within the territory of India. This establishes the doctrine of precedent in India."
    },
    {
        "q_no": 63,
        "question": "Which statement about G-20 is NOT correct?",
        "options": ["(A) Established in 1999", "(B) USA hosted first summit in 2008", "(C) Presidency rotates yearly", "(D) Chile is a member"],
        "answer": "D",
        "explanation": "Chile is NOT a member of G20.",
        "narration_q": "Question 63. Which of the following statements about G 20 is NOT correct?",
        "narration_a": "The correct answer is Option D. Chile is not a member of the G 20. The G 20 consists of 19 countries plus the European Union and the African Union. Chile has been invited as a guest but is not an official member."
    },
    {
        "q_no": 64,
        "question": "HSRA ideology was inspired by:",
        "options": ["(A) Italian movement and Mazzini", "(B) Leninist Communism", "(C) American War of Independence", "(D) Irish freedom struggle and Sinn Fein"],
        "answer": "D",
        "explanation": "HSRA was inspired by the Irish freedom struggle and Sinn Fein Movement.",
        "narration_q": "Question 64. The foundational ideology of the Hindustan Socialist Republican Association was inspired by what?",
        "narration_a": "The correct answer is Option D. The Irish freedom struggle and Sinn Fein Movement. The HSRA, founded in 1928 by Bhagat Singh and Chandrashekhar Azad, drew inspiration from the Irish model of armed resistance against British colonialism."
    },
    {
        "q_no": 65,
        "question": "Which fundamental right is only for Indian citizens?",
        "options": ["(A) Article 14 - Equality", "(B) Article 19 - Speech", "(C) Article 20 - Protection", "(D) Article 21 - Life and Liberty"],
        "answer": "B",
        "explanation": "Article 19 freedoms are available ONLY to citizens, not foreigners.",
        "narration_q": "Question 65. Which fundamental right is available only to Indian citizens and not to foreigners?",
        "narration_a": "The correct answer is Option B. Freedom of Speech and Expression under Article 19. Articles 14, 20, and 21 are available to all persons including foreigners. But Article 19 guarantees six freedoms exclusively to citizens of India."
    },
    {
        "q_no": 66,
        "question": "Match Geological Structure with Economic Importance:",
        "options": ["(A) 2 1 3 4", "(B) 3 2 1 4", "(C) 3 2 4 1", "(D) 2 4 1 3"],
        "answer": "C",
        "explanation": "Siwalik-fossils, Deccan Traps-black cotton soils, Singhbhum-iron ore, Chhota Nagpur-coal/mica.",
        "narration_q": "Question 66. Match the geological structures with their economic importance.",
        "narration_a": "The correct answer is Option C. Siwalik Hills have fossil-rich sedimentary deposits. Deccan Traps produce black cotton soils ideal for sugarcane. Singhbhum Craton is rich in iron ore. And Chhota Nagpur Plateau is India's mineral heartland with coal, mica, and uranium."
    },
    {
        "q_no": 67,
        "question": "India's rank in Global Hunger Index 2023?",
        "options": ["(A) 105", "(B) 107", "(C) 111", "(D) 115"],
        "answer": "C",
        "explanation": "India ranked 111th out of 125 countries in GHI 2023.",
        "narration_q": "Question 67. As per the Global Hunger Index 2023, India ranks at which position globally?",
        "narration_a": "The correct answer is Option C. 111. India ranked 111th out of 125 countries in the Global Hunger Index 2023 with a score of 28.7, categorized as Serious. This was below neighbors like Nepal, Bangladesh, and Sri Lanka."
    },
    {
        "q_no": 68,
        "question": "Statements about ecological pyramids:",
        "options": ["(A) 1 only", "(B) 2 and 3 only", "(C) 1 and 3 only", "(D) 1, 2 and 3"],
        "answer": "C",
        "explanation": "Statement 2 is incorrect. Pyramids of energy are NEVER inverted.",
        "narration_q": "Question 68. Consider the statements about ecological pyramids. Which are correct?",
        "narration_a": "The correct answer is Option C. Statements 1 and 3 only. Statement 2 is incorrect because pyramids of biomass are not always inverted in marine ecosystems. Statement 1 is correct that parasitic food chains have upright number pyramids. And statement 3 is correct that energy pyramids are never inverted due to the 10 percent energy transfer law."
    },
    {
        "q_no": 69,
        "question": "Statements about Attorney General of India:",
        "options": ["(A) 1, 2 and 3 only", "(B) 1 and 2 only", "(C) 1, 2 and 4 only", "(D) 2, 3 and 4 only"],
        "answer": "A",
        "explanation": "Statement 4 is wrong - Article 148 is about CAG, not AG.",
        "narration_q": "Question 69. Consider the statements about the Attorney General of India. Which are correct?",
        "narration_a": "The correct answer is Option A. Statements 1, 2, and 3 only. Statement 4 is incorrect because Article 148 relates to the Comptroller and Auditor General, not the Attorney General. The AG's remuneration is determined by the President."
    },
    {
        "q_no": 70,
        "question": "Statements about Chenab Rail Bridge:",
        "options": ["(A) 1 and 3", "(B) 3 only", "(C) 1 only", "(D) 2 and 4"],
        "answer": "D",
        "explanation": "It's the world's highest railway arch bridge, taller than Eiffel Tower.",
        "narration_q": "Question 70. Which statements about the Chenab Rail Bridge are correct?",
        "narration_a": "The correct answer is Option D. Statements 2 and 4 are correct. The Chenab Rail Bridge at 359 meters is the world's highest railway arch bridge and is taller than the Eiffel Tower at 324 meters. It is an arch bridge, not cable-stayed, and it's part of the Udhampur-Srinagar-Baramulla Rail Link, not the Golden Quadrilateral."
    },
    {
        "q_no": 71,
        "question": "Correctly matched Constitutional Schedule:",
        "options": ["(A) 6th - Languages", "(B) 7th - Division of powers", "(C) 8th - Land Reforms", "(D) 9th - Tribal Areas"],
        "answer": "B",
        "explanation": "7th Schedule contains Union List, State List, and Concurrent List.",
        "narration_q": "Question 71. Which pair is correctly matched regarding Schedules of the Indian Constitution?",
        "narration_a": "The correct answer is Option B. The 7th Schedule contains the division of powers between Union and States through three lists: Union List, State List, and Concurrent List. The 8th Schedule lists recognized languages, not the 6th. The 6th Schedule deals with tribal areas."
    },
    {
        "q_no": 72,
        "question": "Which IUCN category is not in Wildlife Protection Act 1972?",
        "options": ["(A) Critically Endangered", "(B) Vulnerable", "(C) Endemic", "(D) Extinct in the Wild"],
        "answer": "C",
        "explanation": "Endemic is a biogeographic term, not an IUCN threat category.",
        "narration_q": "Question 72. Which category under IUCN classification is not directly recognized in the Indian Wildlife Protection Act 1972?",
        "narration_a": "The correct answer is Option C. Endemic. Endemic is not an IUCN threat category. It's a biogeographic term meaning a species is native to a specific location. IUCN threat categories include Critically Endangered, Vulnerable, Endangered, and Extinct in the Wild."
    },
    {
        "q_no": 73,
        "question": "Acetylsalicylic acid is known as:",
        "options": ["(A) Oil of wintergreen", "(B) Aspirin", "(C) Ibuprofen", "(D) Paracetamol"],
        "answer": "B",
        "explanation": "Acetylsalicylic acid is the chemical name for Aspirin.",
        "narration_q": "Question 73. Acetylsalicylic acid is commonly known as what?",
        "narration_a": "The correct answer is Option B. Aspirin. Acetylsalicylic acid is the chemical name for Aspirin, discovered by Felix Hoffmann at Bayer in 1897. It's used as a pain reliever, anti-inflammatory, and blood thinner. Oil of wintergreen is methyl salicylate, which is a different compound."
    },
    {
        "q_no": 74,
        "question": "Match Odisha personalities with activities:",
        "options": ["(A) a-1, b-2, c-3, d-4", "(B) a-2, b-1, c-3, d-4", "(C) a-4, b-2, c-1, d-3", "(D) a-1, b-3, c-4, d-2"],
        "answer": "B",
        "explanation": "Madhusudan Das-Utkal Sammilani, Buxi Jagabandhu-Khurda Rebellion, Fakir Mohan-Odia literature pioneer.",
        "narration_q": "Question 74. Match the Odisha personalities with their activities.",
        "narration_a": "The correct answer is Option B. Madhusudan Das founded the Utkal Sammilani. Buxi Jagabandhu led the Paika Rebellion of 1817, the first organized rebellion against the British. Fakir Mohan Senapati was the pioneer of Modern Odia literature. And Krushna Chandra Gajapati played a key role in Odisha's separate province formation."
    },
    {
        "q_no": 75,
        "question": "What does NISAR stand for?",
        "options": ["(A) NASA-ISRO Space and Aeronautics Research", "(B) NASA-ISRO Synthetic Aperture Radar", "(C) National Indian Space Radar", "(D) NASA International Satellite for Advanced Research"],
        "answer": "B",
        "explanation": "NISAR = NASA-ISRO Synthetic Aperture Radar, a joint Earth observation satellite.",
        "narration_q": "Question 75. What does NISAR stand for?",
        "narration_a": "The correct answer is Option B. NASA ISRO Synthetic Aperture Radar. NISAR is a joint Earth observation satellite by NASA and ISRO that will map the entire globe in 12 days, monitoring natural hazards, ice sheets, and ecosystems using advanced radar imaging."
    },
    {
        "q_no": 76,
        "question": "Services Sector in India - which are correct?",
        "options": ["(A) 1, 2 and 3 only", "(B) 1, 3 and 4 only", "(C) 2, 3 and 4 only", "(D) All of the above"],
        "answer": "D",
        "explanation": "All four statements about the services sector are correct.",
        "narration_q": "Question 76. Consider the statements about the services sector in India. Which are correct?",
        "narration_a": "The correct answer is Option D. All of the above. The services sector contributes about 55 percent of India's GDP. Despite this, its employment share is lower than agriculture. Growth has been termed jobless growth. And the IT sector has made India a global service hub."
    },
    {
        "q_no": 77,
        "question": "Assertion about Eastern Ghats Granulite Belt and Reason about mineralisation:",
        "options": ["(A) Both true, R explains A", "(B) Both true, R doesn't explain A", "(C) A true, R false", "(D) A false, R true"],
        "answer": "A",
        "explanation": "Both are true and the mineralisation is a direct consequence of the geological formation.",
        "narration_q": "Question 77. Consider the assertion about the Eastern Ghats Granulite Belt and the reason about mineralisation.",
        "narration_a": "The correct answer is Option A. Both the assertion and reason are true, and the reason correctly explains the assertion. The Eastern Ghats Granulite Belt represents Proterozoic era rocks, and the associated mineral deposits of bauxite, manganese, graphite, and gemstones are a direct consequence of this geological formation."
    },
    {
        "q_no": 78,
        "question": "Match leaders with organisations for depressed classes:",
        "options": ["(A) 3 2 4 1", "(B) 3 1 2 4", "(C) 1 3 2 4", "(D) 4 2 1 3"],
        "answer": "B",
        "explanation": "MC Raja-Association, Jagjivan Ram-League, Ambedkar-Congress, Gandhi-Harijan Sangh.",
        "narration_q": "Question 78. Match the leaders with their organizations for depressed classes.",
        "narration_a": "The correct answer is Option B, giving the order 3, 1, 2, 4. M C Raja founded the All India Depressed Classes Association. Jagjivan Ram led the Depressed Classes League. B R Ambedkar started the Depressed Classes Congress. And Mahatma Gandhi founded the All India Harijan Sangh in 1932."
    },
    {
        "q_no": 79,
        "question": "Ganjam Plates of Shailodbhava dynasty provide info about:",
        "options": ["(A) Genealogy and territorial extent", "(B) Maritime trade with SE Asia", "(C) Mukteshvara temple construction", "(D) Relations with Gupta Empire"],
        "answer": "A",
        "explanation": "The copper plates provide genealogical and territorial information about the rulers.",
        "narration_q": "Question 79. The Ganjam Plates of the Shailodbhava dynasty provide information about which aspect of early Medieval Odisha?",
        "narration_a": "The correct answer is Option A. The genealogy and territorial extent of the Shailodbhava rulers. Copper plate grants were the primary source of historical information about dynasties, their lineage, land grants, and territorial boundaries in ancient and medieval India."
    },
    {
        "q_no": 80,
        "question": "Which Asia Cup statements are NOT correct?",
        "options": ["(A) 1 and 2", "(B) 2 and 3", "(C) 3 and 1", "(D) 4 only"],
        "answer": "D",
        "explanation": "First Asia Cup was in Sharjah UAE, not Colombo Sri Lanka.",
        "narration_q": "Question 80. Which statements about the Asia Cup cricket tournament are NOT correct?",
        "narration_a": "The correct answer is Option D. Only statement 4 is incorrect. The first Asia Cup in 1984 was held in Sharjah, UAE, not in Colombo, Sri Lanka. The other statements correctly describe the tournament as an Asian cricket event organized by the Asian Cricket Council, first held in 1984."
    },
    {
        "q_no": 81,
        "question": "Match Himalayan sub-divisions with characteristics:",
        "options": ["(A) 1 4 2 3", "(B) 3 2 1 4", "(C) 3 2 4 1", "(D) 1 3 4 2"],
        "answer": "C",
        "explanation": "Trans-Himalaya has Karakoram and Ladakh ranges.",
        "narration_q": "Question 81. Match the sub-divisions of the Himalayas with their characteristics.",
        "narration_a": "The correct answer is Option C. Trans-Himalaya includes the Karakoram, Ladakh, and Zaskar ranges. The Greater Himalaya contains unconsolidated sediments forming foothills. Lesser Himalaya contains Mount Everest and Kanchenjunga. And the Siwaliks are known for hill stations like Shimla and Mussoorie."
    },
    {
        "q_no": 82,
        "question": "Statements about Rajya Sabha:",
        "options": ["(A) 1 and 2 only", "(B) 1, 2 and 3 only", "(C) 2 and 4 only", "(D) 1, 2, 3 and 4"],
        "answer": "B",
        "explanation": "Rajya Sabha can NEVER be dissolved, even during National Emergency.",
        "narration_q": "Question 82. Which statements about the Rajya Sabha are correct?",
        "narration_a": "The correct answer is Option B. Statements 1, 2, and 3 are correct. Rajya Sabha is a permanent body that is never dissolved. One third of its members retire every 2 years. The Vice President is the ex-officio Chairman. Statement 4 is wrong because Rajya Sabha cannot be dissolved even during a National Emergency."
    },
    {
        "q_no": 83,
        "question": "Who fought the Battle of Talikota?",
        "options": ["(A) Harihara I", "(B) Devaraya II", "(C) Krishna Deva Raya", "(D) Rama Raya"],
        "answer": "D",
        "explanation": "Rama Raya fought at Talikota in 1565 against combined Deccan Sultanates.",
        "narration_q": "Question 83. Who fought the Battle of Talikota?",
        "narration_a": "The correct answer is Option D. Rama Raya. The Battle of Talikota in 1565, also called the Battle of Rakshasi Tangadi, was fought between the Vijayanagara Empire under Rama Raya and the combined forces of the Deccan Sultanates. Rama Raya's defeat led to the decline of the Vijayanagara Empire."
    },
    {
        "q_no": 84,
        "question": "NDMA functions under:",
        "options": ["(A) Ministry of Environment", "(B) Ministry of Home Affairs", "(C) Cabinet Secretariat", "(D) Prime Minister's Office"],
        "answer": "D",
        "explanation": "NDMA functions under PMO, PM is its ex-officio Chairperson.",
        "narration_q": "Question 84. The National Disaster Management Authority functions under which body?",
        "narration_a": "The correct answer is Option D. The Prime Minister's Office. The Prime Minister is the ex-officio Chairperson of NDMA. It was established under the Disaster Management Act 2005 and reports directly to the PMO."
    },
    {
        "q_no": 85,
        "question": "India's first OECM recognition was for:",
        "options": ["(A) Ex-situ conservation of orchids", "(B) Sacred groves with endemic fauna", "(C) Community forest biodiversity", "(D) Coral reef mapping"],
        "answer": "B",
        "explanation": "First OECM recognition was for sacred groves preserving endemic fauna.",
        "narration_q": "Question 85. India's first OECM recognition was awarded for which reason?",
        "narration_a": "The correct answer is Option B. Sacred groves with endemic fauna. OECMs, or Other Effective area-based Conservation Measures, recognize areas that achieve biodiversity conservation outside traditional protected areas. Sacred groves in India have protected biodiversity for centuries through cultural and religious practices."
    },
    {
        "q_no": 86,
        "question": "Who built Jain Monasteries on Udayagiri Hills?",
        "options": ["(A) Ashoka", "(B) Chandra Gupta Maurya", "(C) Kharavela", "(D) Bindusara"],
        "answer": "C",
        "explanation": "King Kharavela of Kalinga commissioned these rock-cut Jain caves.",
        "narration_q": "Question 86. Who commissioned the construction of the rock-cut Jain Monasteries on Udayagiri Hills?",
        "narration_a": "The correct answer is Option C. King Kharavela of Kalinga, from the 1st century BCE. The Hathigumpha inscription on Udayagiri hill describes his military conquests and patronage of Jain monks. These are among the earliest rock-cut shelters in India."
    },
    {
        "q_no": 87,
        "question": "Tropical Evergreen Forests - which NOT correct?",
        "options": ["(A) 3 and 4 only", "(B) 1 and 2 only", "(C) 2 and 3 only", "(D) 1 and 4 only"],
        "answer": "B",
        "explanation": "Not confined to Eastern Ghats, and evergreen trees don't shed all leaves simultaneously.",
        "narration_q": "Question 87. Which statements about Tropical Evergreen Forests in India are NOT correct?",
        "narration_a": "The correct answer is Option B. Statements 1 and 2 are not correct. Tropical Evergreen Forests are found in Western Ghats, Northeast India, and Andaman Nicobar, not confined to the Eastern Ghats. And being evergreen, they do not shed all leaves simultaneously during the dry season."
    },
    {
        "q_no": 88,
        "question": "What is the Surya Heliophysics Foundation Model?",
        "options": ["(A) Planetary rover", "(B) AI model for solar activity", "(C) Earth observation satellite", "(D) Spacecraft"],
        "answer": "B",
        "explanation": "It's an AI model to forecast solar activity and space weather.",
        "narration_q": "Question 88. What is the Surya Heliophysics Foundation Model?",
        "narration_a": "The correct answer is Option B. An AI model to forecast solar activity. It uses deep learning to analyze solar data and predict solar flares, coronal mass ejections, and space weather events that could impact Earth's technology systems and satellites."
    },
    {
        "q_no": 89,
        "question": "Arrange Raja Ram Mohan Roy's institutions chronologically:",
        "options": ["(A) d, a, b, c", "(B) c, a, b, d", "(C) b, d, c, a", "(D) a, c, b, d"],
        "answer": "B",
        "explanation": "Atmiya Sabha (1815), Unitarian Committee, Vedanta College (1825), Brahmo Samaj (1828).",
        "narration_q": "Question 89. Arrange the religious institutions established by Raja Ram Mohan Roy in chronological order.",
        "narration_a": "The correct answer is Option B. The order is: Atmiya Sabha in 1815, then the Unitarian Committee, followed by Vedanta College in 1825, and finally Brahmo Samaj in 1828, which was his most famous reform movement."
    },
    {
        "q_no": 90,
        "question": "India's Multidimensional Poverty Index statements:",
        "options": ["(A) 1 and 2 only", "(B) 1, 2 and 4 only", "(C) 2 and 3 only", "(D) All of the above"],
        "answer": "D",
        "explanation": "All four statements about MPI are correct.",
        "narration_q": "Question 90. Consider the statements about India's Multidimensional Poverty Index. Which are correct?",
        "narration_a": "The correct answer is Option D. All of the above. India's MPI uses three dimensions: health, education, and standard of living. It is published by NITI Aayog using NFHS data. The Global MPI is released by UNDP and OPHI. And indicators include nutrition, school attendance, and access to clean cooking fuel."
    },
    {
        "q_no": 91,
        "question": "'One Health' approach refers to:",
        "options": ["(A) Integrating traditional and modern health", "(B) Linking human, animal and environmental health", "(C) Public and private hospitals jointly", "(D) Telemedicine for rural areas"],
        "answer": "B",
        "explanation": "One Health links human, animal, and environmental health to prevent pandemics.",
        "narration_q": "Question 91. The One Health approach in public policy refers to what?",
        "narration_a": "The correct answer is Option B. Linking human, animal, and environmental health to prevent pandemics. The One Health approach recognizes that 70 percent of emerging infectious diseases are zoonotic, originating from animals, making this integrated approach critical for pandemic prevention."
    },
    {
        "q_no": 92,
        "question": "OIIPCRA - which statement is NOT correct?",
        "options": ["(A) 1 only", "(B) 2 only", "(C) 3 only", "(D) 4 only"],
        "answer": "C",
        "explanation": "Statement 3 is wrong - OIIPCRA doesn't focus on large-scale dam construction.",
        "narration_q": "Question 92. Which statement about the Odisha Integrated Irrigation Project for Climate Resilient Agriculture is NOT correct?",
        "narration_a": "The correct answer is Option C. Statement 3 is not correct. OIIPCRA does not primarily focus on large-scale dam construction. Instead, it focuses on modernizing existing irrigation infrastructure, promoting micro-irrigation, and climate-resilient agriculture practices."
    },
    {
        "q_no": 93,
        "question": "Author of 'Baidehisha Bilasa'?",
        "options": ["(A) Hari Charan Deva", "(B) Sisu Sankar Das", "(C) Upendra Bhanja", "(D) Harihar Kabi"],
        "answer": "C",
        "explanation": "Upendra Bhanja, the greatest ornate poet of Odia literature, wrote this masterpiece.",
        "narration_q": "Question 93. Who is the author of the book Baidehisha Bilasa?",
        "narration_a": "The correct answer is Option C. Upendra Bhanja. He lived from 1670 to 1720 and is considered the greatest ornate poet, or Kabi Samrat, of Odia literature. He belonged to the Bhanja dynasty of Ghumsar in southern Odisha."
    },
    {
        "q_no": 94,
        "question": "Biosphere Reserves - which NOT correct?",
        "options": ["(A) 3 only", "(B) 1 and 3 only", "(C) 1, 2 and 4 only", "(D) 3 and 4 only"],
        "answer": "A",
        "explanation": "Statement 3 is wrong - there ARE biosphere reserves in the Himalayan region.",
        "narration_q": "Question 94. Which statements about Biosphere Reserves in India are NOT correct?",
        "narration_a": "The correct answer is Option A. Only statement 3 is incorrect. There are indeed biosphere reserves in the Himalayan region, such as Nanda Devi, Cold Desert in Himachal Pradesh, and Khangchendzonga. All other statements about Great Nicobar, Nilgiri, and Sundarbans are correct."
    },
    {
        "q_no": 95,
        "question": "Mission Karmayogi is aimed at:",
        "options": ["(A) Skill development for youth", "(B) Capacity building of civil servants", "(C) Panchayati Raj training", "(D) Military disaster training"],
        "answer": "B",
        "explanation": "Mission Karmayogi is for capacity building of civil servants through iGOT platform.",
        "narration_q": "Question 95. The Mission Karmayogi launched by the Government of India is aimed at what?",
        "narration_a": "The correct answer is Option B. Capacity building and competency development of civil servants. Launched in 2020, Mission Karmayogi creates a competency framework for government officials through the iGOT platform, the Integrated Government Online Training platform."
    },
    {
        "q_no": 96,
        "question": "Threatened Species Recovery Programme under NBAP targets:",
        "options": ["(A) Locally extinct but globally common", "(B) Keystone species", "(C) Narrow range, declining population", "(D) Genetically engineered species"],
        "answer": "C",
        "explanation": "Targets species with narrow geographic range and declining populations.",
        "narration_q": "Question 96. The Threatened Species Recovery Programme under NBAP targets which type of species?",
        "narration_a": "The correct answer is Option C. Species with narrow geographic range and declining population. These are the species most at risk of extinction and need targeted conservation interventions focusing on habitat-specific, range-restricted species."
    },
    {
        "q_no": 97,
        "question": "Which Mughal Emperor made Odisha a separate Subah?",
        "options": ["(A) Akbar, 1593", "(B) Aurangzeb, 1658", "(C) Shahjahan, 1628", "(D) Jahangir, 1607"],
        "answer": "C",
        "explanation": "Shah Jahan made Odisha a separate Subah in 1628.",
        "narration_q": "Question 97. Which Mughal Emperor appointed the first separate Subahdar of Odisha?",
        "narration_a": "The correct answer is Option C. Shah Jahan in 1628. Before this, Odisha was part of the Bengal Subah. Shah Jahan recognized its administrative importance and made it a separate province with its own governor."
    },
    {
        "q_no": 98,
        "question": "Match 2024-25 summits with host cities:",
        "options": ["(A) a-1 b-2 c-3 d-4", "(B) a-2 b-3 c-4 d-1", "(C) a-1 b-3 c-4 d-2", "(D) a-3 b-2 c-1 d-4"],
        "answer": "A",
        "explanation": "G7-Kananaskis, NATO-The Hague, SCO-Islamabad, G20-Johannesburg.",
        "narration_q": "Question 98. Match the international summits with their host cities.",
        "narration_a": "The correct answer is Option A. The G7 summit 2025 was in Kananaskis, Canada. NATO 2025 in The Hague, Netherlands. SCO 2024 in Islamabad, Pakistan. And the G20 Summit 2025 in Johannesburg, South Africa."
    },
    {
        "q_no": 99,
        "question": "El Nino phenomenon is associated with:",
        "options": ["(A) Weakening of monsoon", "(B) Strengthening of monsoon", "(C) No effect on monsoon", "(D) Only winter rains"],
        "answer": "A",
        "explanation": "El Nino weakens the Indian monsoon, historically causing droughts.",
        "narration_q": "Question 99. The El Nino phenomenon is associated with what effect on India?",
        "narration_a": "The correct answer is Option A. Weakening of the monsoon in India. During El Nino years, the temperature gradient between the Indian Ocean and Pacific weakens, reducing monsoon rains. Major droughts in 1972, 1987, 2002, and 2009 coincided with El Nino events."
    },
    {
        "q_no": 100,
        "question": "India defeated which country in Kho Kho World Cup 2025 finals?",
        "options": ["(A) Bangladesh", "(B) Sri Lanka", "(C) Nepal", "(D) Pakistan"],
        "answer": "C",
        "explanation": "India defeated Nepal in both men's and women's Kho Kho World Cup 2025 finals.",
        "narration_q": "Question 100. Which country did India defeat in both men's and women's Kho Kho World Cup 2025 finals?",
        "narration_a": "The correct answer is Option C. Nepal. India defeated Nepal in both the men's and women's finals of the inaugural Kho Kho World Cup 2025, held in New Delhi. This showcased the growing international appeal of this traditional Indian sport. Congratulations on completing all 100 questions!"
    }
]


# ── VISUAL FRAME FUNCTIONS (reused from previous script) ────────────────

def get_font(bold=False, size=32):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)

def draw_rounded_rect(draw, xy, radius, fill, outline=None, width=0):
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)

def wrap_text(text, font, max_width, draw):
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        words = paragraph.split(' ')
        current_line = ''
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
    return lines

def draw_gradient_bg(img, color_top=(10, 10, 35), color_bottom=(25, 20, 50)):
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        ratio = y / h
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        for x in range(w):
            pixels[x, y] = (r, g, b)

def draw_progress_bar(draw, x, y, w, h, progress, color=ACCENT_BLUE):
    draw_rounded_rect(draw, (x, y, x + w, y + h), 8, fill=(40, 45, 70))
    fill_w = int(w * progress)
    if fill_w > 0:
        draw_rounded_rect(draw, (x, y, x + fill_w, y + h), 8, fill=color)

def draw_decorative_line(draw, y, width=1920, color=ACCENT_BLUE, thickness=2):
    draw.line([(60, y), (width - 60, y)], fill=color, width=thickness)

def create_intro_frame():
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw_gradient_bg(img, (5, 5, 25), (20, 15, 45))
    draw = ImageDraw.Draw(img)
    draw_rounded_rect(draw, (0, 0, WIDTH, 6), 0, fill=ACCENT_BLUE)
    title_font = get_font(True, 58)
    subtitle_font = get_font(True, 38)
    detail_font = get_font(False, 30)
    title = "OPSC OCS PRELIMS 2024"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = (WIDTH - tw) // 2
    for offset in [(2,2), (-2,-2), (2,-2), (-2,2)]:
        draw.text((tx + offset[0], 280 + offset[1]), title, fill=(0, 80, 180), font=title_font)
    draw.text((tx, 280), title, fill=GOLD, font=title_font)
    sub = "Paper-I (General Studies) - Complete Solution"
    bbox = draw.textbbox((0, 0), sub, font=subtitle_font)
    sw = bbox[2] - bbox[0]
    draw.text(((WIDTH - sw) // 2, 360), sub, fill=TEXT_WHITE, font=subtitle_font)
    draw_decorative_line(draw, 420, color=GOLD)
    details = ["100 Questions with Detailed Explanations", "Correct Answers + AI Voice Narration", "Exam Code: CSP-24/I/C  |  Series: K-75"]
    y = 460
    for d in details:
        bbox = draw.textbbox((0, 0), d, font=detail_font)
        dw = bbox[2] - bbox[0]
        draw.text(((WIDTH - dw) // 2, y), d, fill=TEXT_LIGHT, font=detail_font)
        y += 50
    draw_rounded_rect(draw, (500, 640, 1420, 780), 15, fill=(30, 35, 65), outline=ACCENT_BLUE, width=2)
    info_font = get_font(True, 28)
    draw.text((570, 660), "Odisha Public Service Commission", fill=ACCENT_ORANGE, font=info_font)
    draw.text((560, 705), "Previous Year Question Paper Analysis", fill=ACCENT_ORANGE, font=info_font)
    draw.text((WIDTH // 2 - 200, 850), "Subscribe for more exam solutions!", fill=TEXT_DIM, font=get_font(False, 24))
    draw_rounded_rect(draw, (0, HEIGHT - 6, WIDTH, HEIGHT), 0, fill=ACCENT_BLUE)
    return img

def create_section_divider(section_name, q_range, color=ACCENT_BLUE):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw_gradient_bg(img, (8, 8, 30), (20, 15, 45))
    draw = ImageDraw.Draw(img)
    title_font = get_font(True, 52)
    range_font = get_font(True, 36)
    bbox = draw.textbbox((0, 0), section_name, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 400), section_name, fill=color, font=title_font)
    draw_decorative_line(draw, 480, color=color)
    bbox = draw.textbbox((0, 0), q_range, font=range_font)
    rw = bbox[2] - bbox[0]
    draw.text(((WIDTH - rw) // 2, 510), q_range, fill=TEXT_LIGHT, font=range_font)
    return img

def create_question_frame(q_data, total=100):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw_gradient_bg(img, (8, 8, 28), (18, 15, 40))
    draw = ImageDraw.Draw(img)
    q_no = q_data['q_no']
    progress = q_no / total
    draw_rounded_rect(draw, (0, 0, WIDTH, 70), 0, fill=(20, 25, 50))
    draw.text((40, 18), f"Question {q_no} / {total}", fill=GOLD, font=get_font(True, 28))
    draw_progress_bar(draw, 400, 25, 600, 20, progress, ACCENT_BLUE)
    draw.text((1020, 18), f"{int(progress * 100)}%", fill=TEXT_LIGHT, font=get_font(False, 22))
    draw.text((1400, 18), "OPSC OCS 2024 | Paper-I", fill=TEXT_DIM, font=get_font(False, 22))
    card_top, card_bottom = 90, 580
    draw_rounded_rect(draw, (40, card_top, WIDTH - 40, card_bottom), 15, fill=(25, 30, 55), outline=(50, 60, 100), width=1)
    draw_rounded_rect(draw, (60, card_top + 10, 220, card_top + 45), 8, fill=ACCENT_BLUE)
    draw.text((75, card_top + 13), f"QUESTION {q_no}", fill=TEXT_WHITE, font=get_font(True, 22))
    q_lines = wrap_text(q_data['question'], get_font(False, 26), WIDTH - 140, draw)
    y = card_top + 60
    for line in q_lines:
        if y > card_bottom - 30: break
        draw.text((70, y), line, fill=TEXT_WHITE, font=get_font(False, 26))
        y += 36
    opt_y = card_bottom + 20
    option_labels = ['A', 'B', 'C', 'D']
    for i, opt in enumerate(q_data['options']):
        opt_text = opt
        for prefix in ['(A)', '(B)', '(C)', '(D)', 'a)', 'b)', 'c)', 'd)']:
            if opt_text.strip().startswith(prefix):
                opt_text = opt_text.strip()[len(prefix):].strip()
                break
        draw_rounded_rect(draw, (60, opt_y, WIDTH - 60, opt_y + 55), 10, fill=(30, 35, 60), outline=(60, 65, 90), width=1)
        cx, cy = 95, opt_y + 27
        draw.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=(50, 60, 100), outline=ACCENT_BLUE, width=1)
        lf = get_font(True, 22)
        bbox = draw.textbbox((0, 0), option_labels[i], font=lf)
        draw.text((cx - (bbox[2]-bbox[0])//2, cy - 12), option_labels[i], fill=TEXT_WHITE, font=lf)
        draw.text((130, opt_y + 12), opt_text[:100], fill=TEXT_LIGHT, font=get_font(False, 26))
        opt_y += 65
    draw_rounded_rect(draw, (0, HEIGHT - 4, WIDTH, HEIGHT), 0, fill=ACCENT_BLUE)
    return img

def create_answer_frame(q_data, total=100):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw_gradient_bg(img, (8, 8, 28), (18, 15, 40))
    draw = ImageDraw.Draw(img)
    q_no, answer = q_data['q_no'], q_data['answer']
    progress = q_no / total
    draw_rounded_rect(draw, (0, 0, WIDTH, 70), 0, fill=(20, 25, 50))
    draw.text((40, 18), f"Answer {q_no} / {total}", fill=GOLD, font=get_font(True, 28))
    draw_progress_bar(draw, 400, 25, 600, 20, progress, ACCENT_GREEN)
    draw.text((1400, 18), "OPSC OCS 2024 | Paper-I", fill=TEXT_DIM, font=get_font(False, 22))
    answer_y = 85
    draw_rounded_rect(draw, (40, answer_y, WIDTH - 40, answer_y + 70), 12, fill=(15, 60, 35), outline=ACCENT_GREEN, width=2)
    ans_idx = ord(answer) - ord('A')
    ans_label = f"Correct Answer: ({answer})"
    if ans_idx < len(q_data['options']):
        ans_label += f"  -  {q_data['options'][ans_idx]}"
    if len(ans_label) > 80: ans_label = ans_label[:77] + "..."
    draw.text((80, answer_y + 18), ans_label, fill=ACCENT_GREEN, font=get_font(True, 28))
    opt_y = answer_y + 85
    option_labels = ['A', 'B', 'C', 'D']
    for i, opt in enumerate(q_data['options']):
        opt_text = opt
        for prefix in ['(A)', '(B)', '(C)', '(D)', 'a)', 'b)', 'c)', 'd)']:
            if opt_text.strip().startswith(prefix):
                opt_text = opt_text.strip()[len(prefix):].strip()
                break
        is_correct = (option_labels[i] == answer)
        if is_correct:
            card_color, border_color, text_color, circle_fill = (15, 55, 30), ACCENT_GREEN, ACCENT_GREEN, ACCENT_GREEN
        else:
            card_color, border_color, text_color, circle_fill = (35, 25, 25), (80, 40, 40), (180, 100, 100), ACCENT_RED
        draw_rounded_rect(draw, (60, opt_y, WIDTH - 60, opt_y + 45), 8, fill=card_color, outline=border_color, width=1)
        cx, cy = 90, opt_y + 22
        draw.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=circle_fill)
        draw.text((120, opt_y + 10), opt_text[:90], fill=text_color, font=get_font(False, 24))
        if is_correct:
            draw.text((WIDTH - 110, opt_y + 8), "✓", fill=ACCENT_GREEN, font=get_font(True, 24))
        else:
            draw.text((WIDTH - 110, opt_y + 8), "✗", fill=ACCENT_RED, font=get_font(True, 24))
        opt_y += 52
    exp_top = opt_y + 15
    exp_bottom = HEIGHT - 20
    draw_rounded_rect(draw, (40, exp_top, WIDTH - 40, exp_bottom), 12, fill=(25, 28, 50), outline=ACCENT_ORANGE, width=1)
    draw_rounded_rect(draw, (55, exp_top + 8, 250, exp_top + 40), 8, fill=ACCENT_ORANGE)
    draw.text((70, exp_top + 10), "EXPLANATION", fill=BG_DARK, font=get_font(True, 20))
    exp_lines = wrap_text(q_data['explanation'], get_font(False, 22), WIDTH - 160, draw)
    ey = exp_top + 50
    for line in exp_lines:
        if ey > exp_bottom - 25: break
        color = ACCENT_ORANGE if line.strip().startswith(('•', '-')) else TEXT_LIGHT
        draw.text((70, ey), line, fill=color, font=get_font(False, 22))
        ey += 30
    draw_rounded_rect(draw, (0, HEIGHT - 4, WIDTH, HEIGHT), 0, fill=ACCENT_GREEN)
    return img

def create_outro_frame():
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_DARK)
    draw_gradient_bg(img, (5, 5, 25), (20, 15, 45))
    draw = ImageDraw.Draw(img)
    draw_rounded_rect(draw, (0, 0, WIDTH, 6), 0, fill=GOLD)
    title_font, sub_font, detail_font = get_font(True, 52), get_font(True, 36), get_font(False, 28)
    text = "Thank You for Watching!"
    bbox = draw.textbbox((0, 0), text, font=title_font)
    draw.text(((WIDTH - (bbox[2]-bbox[0])) // 2, 300), text, fill=GOLD, font=title_font)
    draw_decorative_line(draw, 380, color=GOLD)
    msgs = [("All 100 Questions Solved with Explanations", detail_font, TEXT_LIGHT),
            ("", None, None), ("LIKE  |  SHARE  |  SUBSCRIBE", sub_font, ACCENT_ORANGE),
            ("", None, None), ("Comment your score below!", detail_font, TEXT_LIGHT),
            ("", None, None), ("More OPSC OCS preparation videos coming soon...", detail_font, TEXT_LIGHT)]
    y = 420
    for msg, f, c in msgs:
        if not msg: y += 20; continue
        bbox = draw.textbbox((0, 0), msg, font=f)
        draw.text(((WIDTH - (bbox[2]-bbox[0])) // 2, y), msg, fill=c, font=f)
        y += 50
    draw_rounded_rect(draw, (0, HEIGHT - 6, WIDTH, HEIGHT), 0, fill=GOLD)
    return img


# ── TTS AUDIO GENERATION ───────────────────────────────────────────────

async def generate_audio_clip(text, output_path, voice=VOICE, rate=RATE):
    """Generate a single TTS audio clip."""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def get_audio_duration(filepath):
    """Get duration of audio file using ffprobe."""
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])


async def generate_all_audio():
    """Generate all TTS audio clips."""
    print("\n[AUDIO] Generating TTS narration for all questions...")

    audio_entries = []  # (audio_path, type, q_no)

    # Import Hindi narrations
    from hindi_narrations import HINDI_NARRATIONS

    # Intro narration in Hindi
    intro_text = "OPSC OCS प्रीलिम्स 2024 के कंप्लीट सॉल्यूशन वीडियो में आपका स्वागत है। इस वीडियो में हम पेपर 1 जनरल स्टडीज के सभी 100 प्रश्नों को विस्तृत व्याख्या के साथ हल करेंगे। तो चलिए शुरू करते हैं!"
    intro_path = os.path.join(AUDIO_DIR, "intro.mp3")
    if not os.path.exists(intro_path):
        await generate_audio_clip(intro_text, intro_path)
    audio_entries.append(("intro", intro_path, 0))

    # Section narrations in Hindi
    section_texts = [
        "सेक्शन 1. राजनीति, इतिहास और शासन। प्रश्न 1 से 25।",
        "सेक्शन 2. भूगोल, अर्थव्यवस्था और पर्यावरण। प्रश्न 26 से 50।",
        "सेक्शन 3. विज्ञान, प्रौद्योगिकी और करेंट अफेयर्स। प्रश्न 51 से 75।",
        "सेक्शन 4. ओडिशा विशेष और विविध। प्रश्न 76 से 100।"
    ]
    for i, st in enumerate(section_texts):
        spath = os.path.join(AUDIO_DIR, f"section_{i}.mp3")
        if not os.path.exists(spath):
            await generate_audio_clip(st, spath)
        audio_entries.append(("section", spath, i))

    # Question and answer narrations - use Hindi from separate file
    for q in QUESTIONS:
        qn = q['q_no']
        q_path = os.path.join(AUDIO_DIR, f"q_{qn:03d}.mp3")
        a_path = os.path.join(AUDIO_DIR, f"a_{qn:03d}.mp3")

        hindi_q, hindi_a = HINDI_NARRATIONS[qn]

        if not os.path.exists(q_path):
            await generate_audio_clip(hindi_q, q_path)
        if not os.path.exists(a_path):
            await generate_audio_clip(hindi_a, a_path)

        audio_entries.append(("question", q_path, qn))
        audio_entries.append(("answer", a_path, qn))

        if qn % 10 == 0:
            print(f"   ... generated audio for {qn}/100 questions")

    # Outro narration in Hindi
    outro_text = "OPSC OCS प्रीलिम्स 2024 पेपर 1 के सभी 100 प्रश्न पूरे हुए। अगर यह वीडियो आपके लिए उपयोगी रही तो कृपया लाइक, शेयर और सब्सक्राइब करें। अपना स्कोर नीचे कमेंट में बताएं। आपकी तैयारी के लिए शुभकामनाएं!"
    outro_path = os.path.join(AUDIO_DIR, "outro.mp3")
    if not os.path.exists(outro_path):
        await generate_audio_clip(outro_text, outro_path)
    audio_entries.append(("outro", outro_path, 0))

    return audio_entries


# ── MAIN VIDEO GENERATION ──────────────────────────────────────────────

def generate_video():
    """Generate video with audio narration."""
    print("=" * 60)
    print("OPSC OCS PRELIMS 2024 - Video + Audio Generator")
    print("=" * 60)

    # Step 1: Generate all audio
    audio_entries = asyncio.run(generate_all_audio())

    # Step 2: Get audio durations and create frame+audio pairs
    print("\n[VIDEO] Creating visual frames and calculating durations...")

    MIN_Q_DURATION = 5  # minimum seconds for question display
    MIN_A_DURATION = 6  # minimum seconds for answer display
    PADDING = 1.5       # extra seconds after audio finishes

    segments = []  # list of (image_path, audio_path, duration)

    # Intro
    intro_img = os.path.join(FRAMES_DIR, "intro.png")
    create_intro_frame().save(intro_img)
    intro_audio = os.path.join(AUDIO_DIR, "intro.mp3")
    intro_dur = max(6, get_audio_duration(intro_audio) + PADDING)
    segments.append((intro_img, intro_audio, intro_dur))

    sections = [
        ("Section 1: Polity & History", "Questions 1-25"),
        ("Section 2: Geography & Economy", "Questions 26-50"),
        ("Section 3: Science & Current Affairs", "Questions 51-75"),
        ("Section 4: Odisha & Miscellaneous", "Questions 76-100"),
    ]
    sec_colors = [ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, PURPLE]

    for idx, q in enumerate(QUESTIONS):
        # Section divider
        if idx % 25 == 0:
            sec_idx = idx // 25
            sec_img = os.path.join(FRAMES_DIR, f"sec_{sec_idx}.png")
            create_section_divider(sections[sec_idx][0], sections[sec_idx][1], sec_colors[sec_idx]).save(sec_img)
            sec_audio = os.path.join(AUDIO_DIR, f"section_{sec_idx}.mp3")
            sec_dur = max(4, get_audio_duration(sec_audio) + PADDING)
            segments.append((sec_img, sec_audio, sec_dur))

        # Question
        q_img = os.path.join(FRAMES_DIR, f"q_{q['q_no']:03d}.png")
        create_question_frame(q).save(q_img)
        q_audio = os.path.join(AUDIO_DIR, f"q_{q['q_no']:03d}.mp3")
        q_dur = max(MIN_Q_DURATION, get_audio_duration(q_audio) + PADDING)
        segments.append((q_img, q_audio, q_dur))

        # Answer
        a_img = os.path.join(FRAMES_DIR, f"a_{q['q_no']:03d}.png")
        create_answer_frame(q).save(a_img)
        a_audio = os.path.join(AUDIO_DIR, f"a_{q['q_no']:03d}.mp3")
        a_dur = max(MIN_A_DURATION, get_audio_duration(a_audio) + PADDING)
        segments.append((a_img, a_audio, a_dur))

        if (idx + 1) % 10 == 0:
            print(f"   ... processed {idx + 1}/100 questions")

    # Outro
    outro_img = os.path.join(FRAMES_DIR, "outro.png")
    create_outro_frame().save(outro_img)
    outro_audio = os.path.join(AUDIO_DIR, "outro.mp3")
    outro_dur = max(8, get_audio_duration(outro_audio) + PADDING)
    segments.append((outro_img, outro_audio, outro_dur))

    total_duration = sum(d for _, _, d in segments)
    print(f"\n   Total segments: {len(segments)}")
    print(f"   Estimated video length: {int(total_duration) // 60}m {int(total_duration) % 60}s")

    # Step 3: Build video using ffmpeg - create each segment then concat
    print("\n[RENDER] Building final video with audio...")

    # Create individual segment videos
    segment_files = []
    for i, (img_path, audio_path, duration) in enumerate(segments):
        seg_file = os.path.join(FRAMES_DIR, f"seg_{i:04d}.mp4")
        abs_img = os.path.abspath(img_path).replace('\\', '/')
        abs_audio = os.path.abspath(audio_path).replace('\\', '/')

        cmd = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', abs_img,
            '-i', abs_audio,
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-tune', 'stillimage',
            '-c:a', 'aac', '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-t', str(round(duration, 2)),
            '-shortest',
            '-r', '24',
            seg_file
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)
        segment_files.append(seg_file)

        if (i + 1) % 20 == 0:
            print(f"   ... rendered {i + 1}/{len(segments)} segments")

    # Step 4: Concat all segments
    print("\n[CONCAT] Joining all segments...")
    concat_file = os.path.join(FRAMES_DIR, "concat.txt")
    with open(concat_file, 'w') as f:
        for sf in segment_files:
            abs_sf = os.path.abspath(sf).replace('\\', '/')
            f.write(f"file '{abs_sf}'\n")

    concat_cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        OUTPUT_FILE
    ]
    result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"Concat error: {result.stderr[-500:]}")
    else:
        file_size = os.path.getsize(OUTPUT_FILE)
        print(f"\n{'=' * 60}")
        print(f"Video saved to: {OUTPUT_FILE}")
        print(f"File size: {file_size / (1024*1024):.1f} MB")
        print(f"Total duration: {int(total_duration) // 60}m {int(total_duration) % 60}s")
        print(f"Voice: {VOICE}")
        print(f"{'=' * 60}")

    # Cleanup segment files (keep audio for re-runs)
    print("Cleaning up temporary segment files...")
    for sf in segment_files:
        if os.path.exists(sf):
            os.remove(sf)
    if os.path.exists(concat_file):
        os.remove(concat_file)
    # Keep frame images dir but remove individual PNGs
    for f in os.listdir(FRAMES_DIR):
        fp = os.path.join(FRAMES_DIR, f)
        if fp.endswith('.png'):
            os.remove(fp)


if __name__ == "__main__":
    generate_video()
