"""Translations of the stretch & mobility flows (2026-11-28): python3 tools/i18n/parts_flows.py.
Machine-style translations like the rest, pending native-speaker review."""
import json

K = [
    "A short break on your feet for the neck, shoulders, back and calves.",
    "After training",
    "Desk break",
    "Gentle mobility for stiff hips and a tired lower back, mostly on the floor.",
    "Hips & lower back",
    "Morning mobility",
    "Slow stretches for the legs, hips, chest and shoulders.",
    "Stretch & mobility flows",
    "Wake up the joints from head to toe, all standing.",
]

T = {
"bg": ["Кратка почивка на крака за врата, раменете, гърба и прасците.", "След тренировка", "Почивка от бюрото", "Нежна мобилност за схванати бедра и уморен кръст, предимно на пода.", "Таз и кръст", "Сутрешна мобилност", "Бавни разтягания за краката, таза, гърдите и раменете.", "Разтягане и мобилност", "Събуди ставите от главата до петите, всичко изправен."],
"cs": ["Krátká přestávka na nohou pro krk, ramena, záda a lýtka.", "Po tréninku", "Přestávka od stolu", "Jemná mobilita pro ztuhlé kyčle a unavená bedra, převážně na zemi.", "Kyčle a bedra", "Ranní mobilita", "Pomalé protažení nohou, kyčlí, hrudníku a ramen.", "Protažení a mobilita", "Probuď klouby od hlavy k patě, vše vestoje."],
"da": ["En kort pause på benene for nakke, skuldre, ryg og lægge.", "Efter træning", "Skrivebordspause", "Blid mobilitet for stive hofter og en træt lænd, mest på gulvet.", "Hofter og lænd", "Morgenmobilitet", "Langsomme stræk for ben, hofter, bryst og skuldre.", "Stræk og mobilitet", "Væk leddene fra top til tå, alt stående."],
"de": ["Eine kurze Pause im Stehen für Nacken, Schultern, Rücken und Waden.", "Nach dem Training", "Schreibtischpause", "Sanfte Mobilität für steife Hüften und einen müden unteren Rücken, meist am Boden.", "Hüfte & unterer Rücken", "Morgen-Mobilität", "Langsame Dehnungen für Beine, Hüfte, Brust und Schultern.", "Dehnen & Mobilität", "Weck die Gelenke von Kopf bis Fuß, alles im Stehen."],
"el": ["Ένα σύντομο διάλειμμα όρθιος για αυχένα, ώμους, πλάτη και γάμπες.", "Μετά την προπόνηση", "Διάλειμμα από το γραφείο", "Ήπια κινητικότητα για σφιγμένους γοφούς και κουρασμένη μέση, κυρίως στο πάτωμα.", "Γοφοί και μέση", "Πρωινή κινητικότητα", "Αργές διατάσεις για πόδια, γοφούς, στήθος και ώμους.", "Διατάσεις και κινητικότητα", "Ξύπνα τις αρθρώσεις από την κορυφή ως τα νύχια, όλα όρθιος."],
"es": ["Una pausa corta de pie para el cuello, los hombros, la espalda y los gemelos.", "Después de entrenar", "Pausa en el escritorio", "Movilidad suave para caderas rígidas y una zona lumbar cansada, sobre todo en el suelo.", "Caderas y zona lumbar", "Movilidad matinal", "Estiramientos lentos para piernas, caderas, pecho y hombros.", "Estiramientos y movilidad", "Despierta las articulaciones de pies a cabeza, todo de pie."],
"et": ["Lühike paus jalgadel kaelale, õlgadele, seljale ja säärtele.", "Pärast treeningut", "Paus laua tagant", "Õrn liikuvus kangetele puusadele ja väsinud alaseljale, peamiselt põrandal.", "Puusad ja alaselg", "Hommikune liikuvus", "Aeglased venitused jalgadele, puusadele, rinnale ja õlgadele.", "Venitus ja liikuvus", "Ärata liigesed peast jalgadeni, kõik seistes."],
"fi": ["Lyhyt tauko jaloillaan niskalle, hartioille, selälle ja pohkeille.", "Treenin jälkeen", "Työpöytätauko", "Lempeää liikkuvuutta jäykille lonkille ja väsyneelle alaselälle, enimmäkseen lattialla.", "Lonkat ja alaselkä", "Aamun liikkuvuus", "Hitaita venytyksiä jaloille, lonkille, rinnalle ja hartioille.", "Venyttely ja liikkuvuus", "Herättele nivelet päästä varpaisiin, kaikki seisten."],
"fr": ["Une courte pause debout pour la nuque, les épaules, le dos et les mollets.", "Après l'entraînement", "Pause bureau", "Une mobilité douce pour des hanches raides et un bas du dos fatigué, surtout au sol.", "Hanches et bas du dos", "Mobilité du matin", "Des étirements lents pour les jambes, les hanches, la poitrine et les épaules.", "Étirements et mobilité", "Réveille les articulations de la tête aux pieds, tout debout."],
"ga": ["Sos gearr ar do chosa don mhuineál, na guaillí, an droim agus na colpaí.", "Tar éis traenála", "Sos ón deasc", "Soghluaisteacht bhog do chromáin righne agus íochtar droma tuirseach, ar an urlár den chuid is mó.", "Cromáin agus íochtar an droma", "Soghluaisteacht na maidine", "Sínte malla do na cosa, na cromáin, an cliabh agus na guaillí.", "Síneadh agus soghluaisteacht", "Múscail na hailt ó bhun go barr, iad ar fad i do sheasamh."],
"hr": ["Kratka pauza na nogama za vrat, ramena, leđa i listove.", "Nakon treninga", "Pauza od stola", "Nježna pokretljivost za ukočene kukove i umoran donji dio leđa, uglavnom na podu.", "Kukovi i donji dio leđa", "Jutarnja pokretljivost", "Polagana istezanja za noge, kukove, prsa i ramena.", "Istezanje i pokretljivost", "Probudi zglobove od glave do pete, sve stojeći."],
"hu": ["Rövid szünet állva a nyaknak, a vállaknak, a hátnak és a vádliknak.", "Edzés után", "Asztali szünet", "Gyengéd mobilitás merev csípőnek és fáradt derékra, főleg a padlón.", "Csípő és derék", "Reggeli mobilitás", "Lassú nyújtások a lábaknak, a csípőnek, a mellkasnak és a vállaknak.", "Nyújtás és mobilitás", "Ébreszd fel az ízületeket tetőtől talpig, mindet állva."],
"it": ["Una breve pausa in piedi per collo, spalle, schiena e polpacci.", "Dopo l'allenamento", "Pausa dalla scrivania", "Mobilità delicata per fianchi rigidi e una zona lombare stanca, per lo più a terra.", "Fianchi e zona lombare", "Mobilità mattutina", "Allungamenti lenti per gambe, fianchi, petto e spalle.", "Stretching e mobilità", "Risveglia le articolazioni dalla testa ai piedi, tutto in piedi."],
"lt": ["Trumpa pertrauka stovint kaklui, pečiams, nugarai ir blauzdoms.", "Po treniruotės", "Pertrauka nuo stalo", "Švelnus judrumas sustingusiems klubams ir pavargusiam juosmeniui, daugiausia ant grindų.", "Klubai ir juosmuo", "Rytinis judrumas", "Lėti tempimai kojoms, klubams, krūtinei ir pečiams.", "Tempimas ir judrumas", "Pažadink sąnarius nuo galvos iki kojų, viskas stovint."],
"lv": ["Īss pārtraukums kājās kaklam, pleciem, mugurai un ikriem.", "Pēc treniņa", "Pārtraukums no galda", "Maigs kustīgums stīviem gurniem un nogurušai jostasvietai, pārsvarā uz grīdas.", "Gurni un jostasvieta", "Rīta kustīgums", "Lēnas stiepšanās kājām, gurniem, krūtīm un pleciem.", "Stiepšanās un kustīgums", "Pamodini locītavas no galvas līdz kājām, viss stāvus."],
"mt": ["Waqfa qasira fuq saqajk għall-għonq, l-ispallejn, id-dahar u l-pexxun.", "Wara t-taħriġ", "Waqfa mill-iskrivanija", "Mobilità ħafifa għal ġenbejn iebsa u parti t'isfel tad-dahar għajjiena, l-aktar fuq l-art.", "Ġenbejn u parti t'isfel tad-dahar", "Mobilità ta' filgħodu", "Stretching bil-mod għar-riġlejn, il-ġenbejn, is-sider u l-ispallejn.", "Stretching u mobilità", "Qajjem il-ġogi mir-ras sa saqajk, kollox bilwieqfa."],
"nl": ["Een korte pauze staand voor nek, schouders, rug en kuiten.", "Na de training", "Bureaupauze", "Zachte mobiliteit voor stijve heupen en een vermoeide onderrug, vooral op de vloer.", "Heupen en onderrug", "Ochtendmobiliteit", "Rustige rekoefeningen voor benen, heupen, borst en schouders.", "Rekken en mobiliteit", "Maak je gewrichten wakker van top tot teen, alles staand."],
"pl": ["Krótka przerwa na stojąco dla szyi, barków, pleców i łydek.", "Po treningu", "Przerwa od biurka", "Łagodna mobilność dla sztywnych bioder i zmęczonego odcinka lędźwiowego, głównie na podłodze.", "Biodra i lędźwie", "Poranna mobilność", "Powolne rozciąganie nóg, bioder, klatki i barków.", "Rozciąganie i mobilność", "Obudź stawy od stóp do głów, wszystko na stojąco."],
"pt": ["Uma pausa curta de pé para o pescoço, os ombros, as costas e as barrigas das pernas.", "Depois do treino", "Pausa da secretária", "Mobilidade suave para ancas rígidas e uma lombar cansada, sobretudo no chão.", "Anca e lombar", "Mobilidade da manhã", "Alongamentos lentos para as pernas, a anca, o peito e os ombros.", "Alongamentos e mobilidade", "Acorda as articulações da cabeça aos pés, tudo de pé."],
"ro": ["O pauză scurtă în picioare pentru gât, umeri, spate și gambe.", "După antrenament", "Pauză de la birou", "Mobilitate blândă pentru șolduri rigide și o zonă lombară obosită, mai ales pe podea.", "Șolduri și zona lombară", "Mobilitate de dimineață", "Întinderi lente pentru picioare, șolduri, piept și umeri.", "Întinderi și mobilitate", "Trezește articulațiile din cap până în picioare, totul în picioare."],
"sk": ["Krátka prestávka na nohách pre krk, ramená, chrbát a lýtka.", "Po tréningu", "Prestávka od stola", "Jemná mobilita pre stuhnuté bedrá a unavené drieky, prevažne na zemi.", "Bedrá a drieky", "Ranná mobilita", "Pomalé strečingy pre nohy, bedrá, hrudník a ramená.", "Strečing a mobilita", "Prebuď kĺby od hlavy po päty, všetko v stoji."],
"sl": ["Kratek odmor na nogah za vrat, ramena, hrbet in mečnice.", "Po vadbi", "Odmor od pisalne mize", "Nežna gibljivost za toge boke in utrujen spodnji del hrbta, večinoma na tleh.", "Boki in spodnji del hrbta", "Jutranja gibljivost", "Počasna raztezanja za noge, boke, prsi in ramena.", "Raztezanje in gibljivost", "Prebudi sklepe od glave do pet, vse stoje."],
"sv": ["En kort paus på fötterna för nacke, axlar, rygg och vader.", "Efter träning", "Skrivbordspaus", "Mjuk rörlighet för stela höfter och en trött ländrygg, mest på golvet.", "Höfter och ländrygg", "Morgonrörlighet", "Långsamma stretchar för ben, höfter, bröst och axlar.", "Stretch och rörlighet", "Väck lederna från topp till tå, allt stående."],
}

if __name__ == "__main__":
    import glob, os
    SRC = json.load(open("tools/i18n/source.json", encoding="utf-8"))
    for p in sorted(glob.glob("app/src/main/assets/i18n/*.json")):
        lang = os.path.basename(p)[:-5]
        rows = T[lang]
        assert len(rows) == len(K), (lang, len(rows))
        t = json.load(open(p, encoding="utf-8"))
        t.update(dict(zip(K, rows)))
        out = {s: t[s] for s in SRC if s in t and str(t[s]).strip()}
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print(lang, len(out), "of", len(SRC))
