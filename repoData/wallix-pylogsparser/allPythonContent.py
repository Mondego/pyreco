__FILENAME__ = domain_parser
# -*- coding: utf-8 -*-

# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""Here we define a function that can parse FQDNs that are IANA compliant."""

tld = set(("ac",
"com.ac",
"edu.ac",
"gov.ac",
"net.ac",
"mil.ac",
"org.ac",
"ad",
"nom.ad",
"ae",
"co.ae",
"net.ae",
"org.ae",
"sch.ae",
"ac.ae",
"gov.ae",
"mil.ae",
"aero",
"accident-investigation.aero",
"accident-prevention.aero",
"aerobatic.aero",
"aeroclub.aero",
"aerodrome.aero",
"agents.aero",
"aircraft.aero",
"airline.aero",
"airport.aero",
"air-surveillance.aero",
"airtraffic.aero",
"air-traffic-control.aero",
"ambulance.aero",
"amusement.aero",
"association.aero",
"author.aero",
"ballooning.aero",
"broker.aero",
"caa.aero",
"cargo.aero",
"catering.aero",
"certification.aero",
"championship.aero",
"charter.aero",
"civilaviation.aero",
"club.aero",
"conference.aero",
"consultant.aero",
"consulting.aero",
"control.aero",
"council.aero",
"crew.aero",
"design.aero",
"dgca.aero",
"educator.aero",
"emergency.aero",
"engine.aero",
"engineer.aero",
"entertainment.aero",
"equipment.aero",
"exchange.aero",
"express.aero",
"federation.aero",
"flight.aero",
"freight.aero",
"fuel.aero",
"gliding.aero",
"government.aero",
"groundhandling.aero",
"group.aero",
"hanggliding.aero",
"homebuilt.aero",
"insurance.aero",
"journal.aero",
"journalist.aero",
"leasing.aero",
"logistics.aero",
"magazine.aero",
"maintenance.aero",
"marketplace.aero",
"media.aero",
"microlight.aero",
"modelling.aero",
"navigation.aero",
"parachuting.aero",
"paragliding.aero",
"passenger-association.aero",
"pilot.aero",
"press.aero",
"production.aero",
"recreation.aero",
"repbody.aero",
"res.aero",
"research.aero",
"rotorcraft.aero",
"safety.aero",
"scientist.aero",
"services.aero",
"show.aero",
"skydiving.aero",
"software.aero",
"student.aero",
"taxi.aero",
"trader.aero",
"trading.aero",
"trainer.aero",
"union.aero",
"workinggroup.aero",
"works.aero",
"af",
"gov.af",
"com.af",
"org.af",
"net.af",
"edu.af",
"ag",
"com.ag",
"org.ag",
"net.ag",
"co.ag",
"nom.ag",
"ai",
"off.ai",
"com.ai",
"net.ai",
"org.ai",
"al",
"com.al",
"edu.al",
"gov.al",
"mil.al",
"net.al",
"org.al",
"am",
"an",
"com.an",
"net.an",
"org.an",
"edu.an",
"ao",
"ed.ao",
"gv.ao",
"og.ao",
"co.ao",
"pb.ao",
"it.ao",
"aq",
"*.ar",
"!congresodelalengua3.ar",
"!educ.ar",
"!gobiernoelectronico.ar",
"!mecon.ar",
"!nacion.ar",
"!nic.ar",
"!promocion.ar",
"!retina.ar",
"!uba.ar",
"e164.arpa",
"in-addr.arpa",
"ip6.arpa",
"iris.arpa",
"uri.arpa",
"urn.arpa",
"as",
"gov.as",
"asia",
"at",
"ac.at",
"co.at",
"gv.at",
"or.at",
"biz.at",
"info.at",
"priv.at",
"*.au",
"act.edu.au",
"nsw.edu.au",
"nt.edu.au",
"qld.edu.au",
"sa.edu.au",
"tas.edu.au",
"vic.edu.au",
"wa.edu.au",
"act.gov.au",
"nt.gov.au",
"qld.gov.au",
"sa.gov.au",
"tas.gov.au",
"vic.gov.au",
"wa.gov.au",
"aw",
"com.aw",
"ax",
"az",
"com.az",
"net.az",
"int.az",
"gov.az",
"org.az",
"edu.az",
"info.az",
"pp.az",
"mil.az",
"name.az",
"pro.az",
"biz.az",
"ba",
"org.ba",
"net.ba",
"edu.ba",
"gov.ba",
"mil.ba",
"unsa.ba",
"unbi.ba",
"co.ba",
"com.ba",
"rs.ba",
"bb",
"biz.bb",
"com.bb",
"edu.bb",
"gov.bb",
"info.bb",
"net.bb",
"org.bb",
"store.bb",
"*.bd",
"be",
"ac.be",
"bf",
"gov.bf",
"bg",
"a.bg",
"b.bg",
"c.bg",
"d.bg",
"e.bg",
"f.bg",
"g.bg",
"h.bg",
"i.bg",
"j.bg",
"k.bg",
"l.bg",
"m.bg",
"n.bg",
"o.bg",
"p.bg",
"q.bg",
"r.bg",
"s.bg",
"t.bg",
"u.bg",
"v.bg",
"w.bg",
"x.bg",
"y.bg",
"z.bg",
"0.bg",
"1.bg",
"2.bg",
"3.bg",
"4.bg",
"5.bg",
"6.bg",
"7.bg",
"8.bg",
"9.bg",
"bh",
"com.bh",
"bi",
"co.bi",
"com.bi",
"edu.bi",
"or.bi",
"org.bi",
"biz",
"bj",
"asso.bj",
"barreau.bj",
"gouv.bj",
"bm",
"com.bm",
"edu.bm",
"gov.bm",
"net.bm",
"org.bm",
"*.bn",
"bo",
"com.bo",
"edu.bo",
"gov.bo",
"gob.bo",
"int.bo",
"org.bo",
"net.bo",
"mil.bo",
"tv.bo",
"br",
"adm.br",
"adv.br",
"agr.br",
"am.br",
"arq.br",
"art.br",
"ato.br",
"bio.br",
"blog.br",
"bmd.br",
"can.br",
"cim.br",
"cng.br",
"cnt.br",
"com.br",
"coop.br",
"ecn.br",
"edu.br",
"eng.br",
"esp.br",
"etc.br",
"eti.br",
"far.br",
"flog.br",
"fm.br",
"fnd.br",
"fot.br",
"fst.br",
"g12.br",
"ggf.br",
"gov.br",
"imb.br",
"ind.br",
"inf.br",
"jor.br",
"jus.br",
"lel.br",
"mat.br",
"med.br",
"mil.br",
"mus.br",
"net.br",
"nom.br",
"not.br",
"ntr.br",
"odo.br",
"org.br",
"ppg.br",
"pro.br",
"psc.br",
"psi.br",
"qsl.br",
"rec.br",
"slg.br",
"srv.br",
"tmp.br",
"trd.br",
"tur.br",
"tv.br",
"vet.br",
"vlog.br",
"wiki.br",
"zlg.br",
"bs",
"com.bs",
"net.bs",
"org.bs",
"edu.bs",
"gov.bs",
"*.bt",
"bw",
"co.bw",
"org.bw",
"by",
"gov.by",
"mil.by",
"com.by",
"of.by",
"bz",
"com.bz",
"net.bz",
"org.bz",
"edu.bz",
"gov.bz",
"ca",
"ab.ca",
"bc.ca",
"mb.ca",
"nb.ca",
"nf.ca",
"nl.ca",
"ns.ca",
"nt.ca",
"nu.ca",
"on.ca",
"pe.ca",
"qc.ca",
"sk.ca",
"yk.ca",
"gc.ca",
"cat",
"cc",
"cd",
"gov.cd",
"cf",
"cg",
"ch",
"ci",
"org.ci",
"or.ci",
"com.ci",
"co.ci",
"edu.ci",
"ed.ci",
"ac.ci",
"net.ci",
"go.ci",
"asso.ci",
"aéroport.ci",
"int.ci",
"presse.ci",
"md.ci",
"gouv.ci",
"*.ck",
"cl",
"gov.cl",
"gob.cl",
"cm",
"gov.cm",
"cn",
"ac.cn",
"com.cn",
"edu.cn",
"gov.cn",
"net.cn",
"org.cn",
"mil.cn",
"公司.cn",
"网络.cn",
"網絡.cn",
"ah.cn",
"bj.cn",
"cq.cn",
"fj.cn",
"gd.cn",
"gs.cn",
"gz.cn",
"gx.cn",
"ha.cn",
"hb.cn",
"he.cn",
"hi.cn",
"hl.cn",
"hn.cn",
"jl.cn",
"js.cn",
"jx.cn",
"ln.cn",
"nm.cn",
"nx.cn",
"qh.cn",
"sc.cn",
"sd.cn",
"sh.cn",
"sn.cn",
"sx.cn",
"tj.cn",
"xj.cn",
"xz.cn",
"yn.cn",
"zj.cn",
"hk.cn",
"mo.cn",
"tw.cn",
"co",
"arts.co",
"com.co",
"edu.co",
"firm.co",
"gov.co",
"info.co",
"int.co",
"mil.co",
"net.co",
"nom.co",
"org.co",
"rec.co",
"web.co",
"com",
"ar.com",
"br.com",
"cn.com",
"de.com",
"eu.com",
"gb.com",
"hu.com",
"jpn.com",
"kr.com",
"no.com",
"qc.com",
"ru.com",
"sa.com",
"se.com",
"uk.com",
"us.com",
"uy.com",
"za.com",
"operaunite.com",
"coop",
"cr",
"ac.cr",
"co.cr",
"ed.cr",
"fi.cr",
"go.cr",
"or.cr",
"sa.cr",
"cu",
"com.cu",
"edu.cu",
"org.cu",
"net.cu",
"gov.cu",
"inf.cu",
"cv",
"cx",
"gov.cx",
"*.cy",
"cz",
"de",
"dj",
"dk",
"dm",
"com.dm",
"net.dm",
"org.dm",
"edu.dm",
"gov.dm",
"*.do",
"dz",
"com.dz",
"org.dz",
"net.dz",
"gov.dz",
"edu.dz",
"asso.dz",
"pol.dz",
"art.dz",
"ec",
"com.ec",
"info.ec",
"net.ec",
"fin.ec",
"k12.ec",
"med.ec",
"pro.ec",
"org.ec",
"edu.ec",
"gov.ec",
"mil.ec",
"edu",
"ee",
"edu.ee",
"gov.ee",
"riik.ee",
"lib.ee",
"med.ee",
"com.ee",
"pri.ee",
"aip.ee",
"org.ee",
"fie.ee",
"*.eg",
"*.er",
"es",
"com.es",
"nom.es",
"org.es",
"gob.es",
"edu.es",
"*.et",
"eu",
"fi",
"aland.fi",
"iki.fi",
"*.fj",
"*.fk",
"fm",
"fo",
"fr",
"com.fr",
"asso.fr",
"nom.fr",
"prd.fr",
"presse.fr",
"tm.fr",
"aeroport.fr",
"assedic.fr",
"avocat.fr",
"avoues.fr",
"cci.fr",
"chambagri.fr",
"chirurgiens-dentistes.fr",
"experts-comptables.fr",
"geometre-expert.fr",
"gouv.fr",
"greta.fr",
"huissier-justice.fr",
"medecin.fr",
"notaires.fr",
"pharmacien.fr",
"port.fr",
"veterinaire.fr",
"ga",
"gd",
"ge",
"com.ge",
"edu.ge",
"gov.ge",
"org.ge",
"mil.ge",
"net.ge",
"pvt.ge",
"gf",
"gg",
"co.gg",
"org.gg",
"net.gg",
"sch.gg",
"gov.gg",
"gh",
"com.gh",
"edu.gh",
"gov.gh",
"org.gh",
"mil.gh",
"gi",
"com.gi",
"ltd.gi",
"gov.gi",
"mod.gi",
"edu.gi",
"org.gi",
"gl",
"gm",
"ac.gn",
"com.gn",
"edu.gn",
"gov.gn",
"org.gn",
"net.gn",
"gov",
"gp",
"com.gp",
"net.gp",
"mobi.gp",
"edu.gp",
"org.gp",
"asso.gp",
"gq",
"gr",
"com.gr",
"edu.gr",
"net.gr",
"org.gr",
"gov.gr",
"gs",
"*.gt",
"*.gu",
"gw",
"gy",
"co.gy",
"com.gy",
"net.gy",
"hk",
"com.hk",
"edu.hk",
"gov.hk",
"idv.hk",
"net.hk",
"org.hk",
"公司.hk",
"教育.hk",
"敎育.hk",
"政府.hk",
"個人.hk",
"个人.hk",
"箇人.hk",
"網络.hk",
"网络.hk",
"组織.hk",
"網絡.hk",
"网絡.hk",
"组织.hk",
"組織.hk",
"組织.hk",
"hm",
"hn",
"com.hn",
"edu.hn",
"org.hn",
"net.hn",
"mil.hn",
"gob.hn",
"hr",
"iz.hr",
"from.hr",
"name.hr",
"com.hr",
"ht",
"com.ht",
"shop.ht",
"firm.ht",
"info.ht",
"adult.ht",
"net.ht",
"pro.ht",
"org.ht",
"med.ht",
"art.ht",
"coop.ht",
"pol.ht",
"asso.ht",
"edu.ht",
"rel.ht",
"gouv.ht",
"perso.ht",
"hu",
"co.hu",
"info.hu",
"org.hu",
"priv.hu",
"sport.hu",
"tm.hu",
"2000.hu",
"agrar.hu",
"bolt.hu",
"casino.hu",
"city.hu",
"erotica.hu",
"erotika.hu",
"film.hu",
"forum.hu",
"games.hu",
"hotel.hu",
"ingatlan.hu",
"jogasz.hu",
"konyvelo.hu",
"lakas.hu",
"media.hu",
"news.hu",
"reklam.hu",
"sex.hu",
"shop.hu",
"suli.hu",
"szex.hu",
"tozsde.hu",
"utazas.hu",
"video.hu",
"*.id",
"ie",
"gov.ie",
"*.il",
"im",
"co.im",
"ltd.co.im",
"plc.co.im",
"net.im",
"gov.im",
"org.im",
"nic.im",
"ac.im",
"in",
"co.in",
"firm.in",
"net.in",
"org.in",
"gen.in",
"ind.in",
"nic.in",
"ac.in",
"edu.in",
"res.in",
"gov.in",
"mil.in",
"info",
"int",
"eu.int",
"io",
"com.io",
"iq",
"gov.iq",
"edu.iq",
"mil.iq",
"com.iq",
"org.iq",
"net.iq",
"ir",
"ac.ir",
"co.ir",
"gov.ir",
"id.ir",
"net.ir",
"org.ir",
"sch.ir",
"is",
"net.is",
"com.is",
"edu.is",
"gov.is",
"org.is",
"int.is",
"it",
"gov.it",
"edu.it",
"agrigento.it",
"ag.it",
"alessandria.it",
"al.it",
"ancona.it",
"an.it",
"aosta.it",
"aoste.it",
"ao.it",
"arezzo.it",
"ar.it",
"ascoli-piceno.it",
"ascolipiceno.it",
"ap.it",
"asti.it",
"at.it",
"avellino.it",
"av.it",
"bari.it",
"ba.it",
"barlettaandriatrani.it",
"barletta-andria-trani.it",
"belluno.it",
"bl.it",
"benevento.it",
"bn.it",
"bergamo.it",
"bg.it",
"biella.it",
"bi.it",
"bologna.it",
"bo.it",
"bolzano.it",
"bozen.it",
"balsan.it",
"alto-adige.it",
"altoadige.it",
"suedtirol.it",
"bz.it",
"brescia.it",
"bs.it",
"brindisi.it",
"br.it",
"cagliari.it",
"ca.it",
"caltanissetta.it",
"cl.it",
"campobasso.it",
"cb.it",
"caserta.it",
"ce.it",
"catania.it",
"ct.it",
"catanzaro.it",
"cz.it",
"chieti.it",
"ch.it",
"como.it",
"co.it",
"cosenza.it",
"cs.it",
"cremona.it",
"cr.it",
"crotone.it",
"kr.it",
"cuneo.it",
"cn.it",
"enna.it",
"en.it",
"fermo.it",
"ferrara.it",
"fe.it",
"firenze.it",
"florence.it",
"fi.it",
"foggia.it",
"fg.it",
"forli-cesena.it",
"forlicesena.it",
"fc.it",
"frosinone.it",
"fr.it",
"genova.it",
"genoa.it",
"ge.it",
"gorizia.it",
"go.it",
"grosseto.it",
"gr.it",
"imperia.it",
"im.it",
"isernia.it",
"is.it",
"laquila.it",
"aquila.it",
"aq.it",
"la-spezia.it",
"laspezia.it",
"sp.it",
"latina.it",
"lt.it",
"lecce.it",
"le.it",
"lecco.it",
"lc.it",
"livorno.it",
"li.it",
"lodi.it",
"lo.it",
"lucca.it",
"lu.it",
"macerata.it",
"mc.it",
"mantova.it",
"mn.it",
"massa-carrara.it",
"massacarrara.it",
"ms.it",
"matera.it",
"mt.it",
"messina.it",
"me.it",
"milano.it",
"milan.it",
"mi.it",
"modena.it",
"mo.it",
"monza.it",
"napoli.it",
"naples.it",
"na.it",
"novara.it",
"no.it",
"nuoro.it",
"nu.it",
"oristano.it",
"or.it",
"padova.it",
"padua.it",
"pd.it",
"palermo.it",
"pa.it",
"parma.it",
"pr.it",
"pavia.it",
"pv.it",
"perugia.it",
"pg.it",
"pescara.it",
"pe.it",
"pesaro-urbino.it",
"pesarourbino.it",
"pu.it",
"piacenza.it",
"pc.it",
"pisa.it",
"pi.it",
"pistoia.it",
"pt.it",
"pordenone.it",
"pn.it",
"potenza.it",
"pz.it",
"prato.it",
"po.it",
"ragusa.it",
"rg.it",
"ravenna.it",
"ra.it",
"reggio-calabria.it",
"reggiocalabria.it",
"rc.it",
"reggio-emilia.it",
"reggioemilia.it",
"re.it",
"rieti.it",
"ri.it",
"rimini.it",
"rn.it",
"roma.it",
"rome.it",
"rm.it",
"rovigo.it",
"ro.it",
"salerno.it",
"sa.it",
"sassari.it",
"ss.it",
"savona.it",
"sv.it",
"siena.it",
"si.it",
"siracusa.it",
"sr.it",
"sondrio.it",
"so.it",
"taranto.it",
"ta.it",
"teramo.it",
"te.it",
"terni.it",
"tr.it",
"torino.it",
"turin.it",
"to.it",
"trapani.it",
"tp.it",
"trento.it",
"trentino.it",
"tn.it",
"treviso.it",
"tv.it",
"trieste.it",
"ts.it",
"udine.it",
"ud.it",
"varese.it",
"va.it",
"venezia.it",
"venice.it",
"ve.it",
"verbania.it",
"vb.it",
"vercelli.it",
"vc.it",
"verona.it",
"vr.it",
"vibo-valentia.it",
"vibovalentia.it",
"vv.it",
"vicenza.it",
"vi.it",
"viterbo.it",
"vt.it",
"je",
"co.je",
"org.je",
"net.je",
"sch.je",
"gov.je",
"*.jm",
"jo",
"com.jo",
"org.jo",
"net.jo",
"edu.jo",
"sch.jo",
"gov.jo",
"mil.jo",
"name.jo",
"jobs",
"jp",
"ac.jp",
"ad.jp",
"co.jp",
"ed.jp",
"go.jp",
"gr.jp",
"lg.jp",
"ne.jp",
"or.jp",
"*.aichi.jp",
"*.akita.jp",
"*.aomori.jp",
"*.chiba.jp",
"*.ehime.jp",
"*.fukui.jp",
"*.fukuoka.jp",
"*.fukushima.jp",
"*.gifu.jp",
"*.gunma.jp",
"*.hiroshima.jp",
"*.hokkaido.jp",
"*.hyogo.jp",
"*.ibaraki.jp",
"*.ishikawa.jp",
"*.iwate.jp",
"*.kagawa.jp",
"*.kagoshima.jp",
"*.kanagawa.jp",
"*.kawasaki.jp",
"*.kitakyushu.jp",
"*.kobe.jp",
"*.kochi.jp",
"*.kumamoto.jp",
"*.kyoto.jp",
"*.mie.jp",
"*.miyagi.jp",
"*.miyazaki.jp",
"*.nagano.jp",
"*.nagasaki.jp",
"*.nagoya.jp",
"*.nara.jp",
"*.niigata.jp",
"*.oita.jp",
"*.okayama.jp",
"*.okinawa.jp",
"*.osaka.jp",
"*.saga.jp",
"*.saitama.jp",
"*.sapporo.jp",
"*.sendai.jp",
"*.shiga.jp",
"*.shimane.jp",
"*.shizuoka.jp",
"*.tochigi.jp",
"*.tokushima.jp",
"*.tokyo.jp",
"*.tottori.jp",
"*.toyama.jp",
"*.wakayama.jp",
"*.yamagata.jp",
"*.yamaguchi.jp",
"*.yamanashi.jp",
"*.yokohama.jp",
"!metro.tokyo.jp",
"!pref.aichi.jp",
"!pref.akita.jp",
"!pref.aomori.jp",
"!pref.chiba.jp",
"!pref.ehime.jp",
"!pref.fukui.jp",
"!pref.fukuoka.jp",
"!pref.fukushima.jp",
"!pref.gifu.jp",
"!pref.gunma.jp",
"!pref.hiroshima.jp",
"!pref.hokkaido.jp",
"!pref.hyogo.jp",
"!pref.ibaraki.jp",
"!pref.ishikawa.jp",
"!pref.iwate.jp",
"!pref.kagawa.jp",
"!pref.kagoshima.jp",
"!pref.kanagawa.jp",
"!pref.kochi.jp",
"!pref.kumamoto.jp",
"!pref.kyoto.jp",
"!pref.mie.jp",
"!pref.miyagi.jp",
"!pref.miyazaki.jp",
"!pref.nagano.jp",
"!pref.nagasaki.jp",
"!pref.nara.jp",
"!pref.niigata.jp",
"!pref.oita.jp",
"!pref.okayama.jp",
"!pref.okinawa.jp",
"!pref.osaka.jp",
"!pref.saga.jp",
"!pref.saitama.jp",
"!pref.shiga.jp",
"!pref.shimane.jp",
"!pref.shizuoka.jp",
"!pref.tochigi.jp",
"!pref.tokushima.jp",
"!pref.tottori.jp",
"!pref.toyama.jp",
"!pref.wakayama.jp",
"!pref.yamagata.jp",
"!pref.yamaguchi.jp",
"!pref.yamanashi.jp",
"!city.chiba.jp",
"!city.fukuoka.jp",
"!city.hiroshima.jp",
"!city.kawasaki.jp",
"!city.kitakyushu.jp",
"!city.kobe.jp",
"!city.kyoto.jp",
"!city.nagoya.jp",
"!city.niigata.jp",
"!city.okayama.jp",
"!city.osaka.jp",
"!city.saitama.jp",
"!city.sapporo.jp",
"!city.sendai.jp",
"!city.shizuoka.jp",
"!city.yokohama.jp",
"*.ke",
"kg",
"org.kg",
"net.kg",
"com.kg",
"edu.kg",
"gov.kg",
"mil.kg",
"*.kh",
"ki",
"edu.ki",
"biz.ki",
"net.ki",
"org.ki",
"gov.ki",
"info.ki",
"com.ki",
"km",
"org.km",
"nom.km",
"gov.km",
"prd.km",
"tm.km",
"edu.km",
"mil.km",
"ass.km",
"com.km",
"coop.km",
"asso.km",
"presse.km",
"medecin.km",
"notaires.km",
"pharmaciens.km",
"veterinaire.km",
"gouv.km",
"kn",
"net.kn",
"org.kn",
"edu.kn",
"gov.kn",
"kr",
"ac.kr",
"co.kr",
"es.kr",
"go.kr",
"hs.kr",
"kg.kr",
"mil.kr",
"ms.kr",
"ne.kr",
"or.kr",
"pe.kr",
"re.kr",
"sc.kr",
"busan.kr",
"chungbuk.kr",
"chungnam.kr",
"daegu.kr",
"daejeon.kr",
"gangwon.kr",
"gwangju.kr",
"gyeongbuk.kr",
"gyeonggi.kr",
"gyeongnam.kr",
"incheon.kr",
"jeju.kr",
"jeonbuk.kr",
"jeonnam.kr",
"seoul.kr",
"ulsan.kr",
"*.kw",
"ky",
"edu.ky",
"gov.ky",
"com.ky",
"org.ky",
"net.ky",
"kz",
"org.kz",
"edu.kz",
"net.kz",
"gov.kz",
"mil.kz",
"com.kz",
"la",
"int.la",
"net.la",
"info.la",
"edu.la",
"gov.la",
"per.la",
"com.la",
"org.la",
"c.la",
"com.lb",
"edu.lb",
"gov.lb",
"net.lb",
"org.lb",
"lc",
"com.lc",
"net.lc",
"co.lc",
"org.lc",
"edu.lc",
"gov.lc",
"li",
"lk",
"gov.lk",
"sch.lk",
"net.lk",
"int.lk",
"com.lk",
"org.lk",
"edu.lk",
"ngo.lk",
"soc.lk",
"web.lk",
"ltd.lk",
"assn.lk",
"grp.lk",
"hotel.lk",
"local",
"com.lr",
"edu.lr",
"gov.lr",
"org.lr",
"net.lr",
"ls",
"co.ls",
"org.ls",
"lt",
"gov.lt",
"lu",
"lv",
"com.lv",
"edu.lv",
"gov.lv",
"org.lv",
"mil.lv",
"id.lv",
"net.lv",
"asn.lv",
"conf.lv",
"ly",
"com.ly",
"net.ly",
"gov.ly",
"plc.ly",
"edu.ly",
"sch.ly",
"med.ly",
"org.ly",
"id.ly",
"ma",
"co.ma",
"net.ma",
"gov.ma",
"org.ma",
"ac.ma",
"press.ma",
"mc",
"tm.mc",
"asso.mc",
"md",
"me",
"co.me",
"net.me",
"org.me",
"edu.me",
"ac.me",
"gov.me",
"its.me",
"priv.me",
"mg",
"org.mg",
"nom.mg",
"gov.mg",
"prd.mg",
"tm.mg",
"edu.mg",
"mil.mg",
"com.mg",
"mh",
"mil",
"mk",
"com.mk",
"org.mk",
"net.mk",
"edu.mk",
"gov.mk",
"inf.mk",
"name.mk",
"ml",
"com.ml",
"edu.ml",
"gouv.ml",
"gov.ml",
"net.ml",
"org.ml",
"presse.ml",
"*.mm",
"mn",
"gov.mn",
"edu.mn",
"org.mn",
"mo",
"com.mo",
"net.mo",
"org.mo",
"edu.mo",
"gov.mo",
"mobi",
"mp",
"mq",
"mr",
"gov.mr",
"ms",
"*.mt",
"mu",
"com.mu",
"net.mu",
"org.mu",
"gov.mu",
"ac.mu",
"co.mu",
"or.mu",
"museum",
"academy.museum",
"agriculture.museum",
"air.museum",
"airguard.museum",
"alabama.museum",
"alaska.museum",
"amber.museum",
"ambulance.museum",
"american.museum",
"americana.museum",
"americanantiques.museum",
"americanart.museum",
"amsterdam.museum",
"and.museum",
"annefrank.museum",
"anthro.museum",
"anthropology.museum",
"antiques.museum",
"aquarium.museum",
"arboretum.museum",
"archaeological.museum",
"archaeology.museum",
"architecture.museum",
"art.museum",
"artanddesign.museum",
"artcenter.museum",
"artdeco.museum",
"arteducation.museum",
"artgallery.museum",
"arts.museum",
"artsandcrafts.museum",
"asmatart.museum",
"assassination.museum",
"assisi.museum",
"association.museum",
"astronomy.museum",
"atlanta.museum",
"austin.museum",
"australia.museum",
"automotive.museum",
"aviation.museum",
"axis.museum",
"badajoz.museum",
"baghdad.museum",
"bahn.museum",
"bale.museum",
"baltimore.museum",
"barcelona.museum",
"baseball.museum",
"basel.museum",
"baths.museum",
"bauern.museum",
"beauxarts.museum",
"beeldengeluid.museum",
"bellevue.museum",
"bergbau.museum",
"berkeley.museum",
"berlin.museum",
"bern.museum",
"bible.museum",
"bilbao.museum",
"bill.museum",
"birdart.museum",
"birthplace.museum",
"bonn.museum",
"boston.museum",
"botanical.museum",
"botanicalgarden.museum",
"botanicgarden.museum",
"botany.museum",
"brandywinevalley.museum",
"brasil.museum",
"bristol.museum",
"british.museum",
"britishcolumbia.museum",
"broadcast.museum",
"brunel.museum",
"brussel.museum",
"brussels.museum",
"bruxelles.museum",
"building.museum",
"burghof.museum",
"bus.museum",
"bushey.museum",
"cadaques.museum",
"california.museum",
"cambridge.museum",
"can.museum",
"canada.museum",
"capebreton.museum",
"carrier.museum",
"cartoonart.museum",
"casadelamoneda.museum",
"castle.museum",
"castres.museum",
"celtic.museum",
"center.museum",
"chattanooga.museum",
"cheltenham.museum",
"chesapeakebay.museum",
"chicago.museum",
"children.museum",
"childrens.museum",
"childrensgarden.museum",
"chiropractic.museum",
"chocolate.museum",
"christiansburg.museum",
"cincinnati.museum",
"cinema.museum",
"circus.museum",
"civilisation.museum",
"civilization.museum",
"civilwar.museum",
"clinton.museum",
"clock.museum",
"coal.museum",
"coastaldefence.museum",
"cody.museum",
"coldwar.museum",
"collection.museum",
"colonialwilliamsburg.museum",
"coloradoplateau.museum",
"columbia.museum",
"columbus.museum",
"communication.museum",
"communications.museum",
"community.museum",
"computer.museum",
"computerhistory.museum",
"comunicações.museum",
"contemporary.museum",
"contemporaryart.museum",
"convent.museum",
"copenhagen.museum",
"corporation.museum",
"correios-e-telecomunicações.museum",
"corvette.museum",
"costume.museum",
"countryestate.museum",
"county.museum",
"crafts.museum",
"cranbrook.museum",
"creation.museum",
"cultural.museum",
"culturalcenter.museum",
"culture.museum",
"cyber.museum",
"cymru.museum",
"dali.museum",
"dallas.museum",
"database.museum",
"ddr.museum",
"decorativearts.museum",
"delaware.museum",
"delmenhorst.museum",
"denmark.museum",
"depot.museum",
"design.museum",
"detroit.museum",
"dinosaur.museum",
"discovery.museum",
"dolls.museum",
"donostia.museum",
"durham.museum",
"eastafrica.museum",
"eastcoast.museum",
"education.museum",
"educational.museum",
"egyptian.museum",
"eisenbahn.museum",
"elburg.museum",
"elvendrell.museum",
"embroidery.museum",
"encyclopedic.museum",
"england.museum",
"entomology.museum",
"environment.museum",
"environmentalconservation.museum",
"epilepsy.museum",
"essex.museum",
"estate.museum",
"ethnology.museum",
"exeter.museum",
"exhibition.museum",
"family.museum",
"farm.museum",
"farmequipment.museum",
"farmers.museum",
"farmstead.museum",
"field.museum",
"figueres.museum",
"filatelia.museum",
"film.museum",
"fineart.museum",
"finearts.museum",
"finland.museum",
"flanders.museum",
"florida.museum",
"force.museum",
"fortmissoula.museum",
"fortworth.museum",
"foundation.museum",
"francaise.museum",
"frankfurt.museum",
"franziskaner.museum",
"freemasonry.museum",
"freiburg.museum",
"fribourg.museum",
"frog.museum",
"fundacio.museum",
"furniture.museum",
"gallery.museum",
"garden.museum",
"gateway.museum",
"geelvinck.museum",
"gemological.museum",
"geology.museum",
"georgia.museum",
"giessen.museum",
"glas.museum",
"glass.museum",
"gorge.museum",
"grandrapids.museum",
"graz.museum",
"guernsey.museum",
"halloffame.museum",
"hamburg.museum",
"handson.museum",
"harvestcelebration.museum",
"hawaii.museum",
"health.museum",
"heimatunduhren.museum",
"hellas.museum",
"helsinki.museum",
"hembygdsforbund.museum",
"heritage.museum",
"histoire.museum",
"historical.museum",
"historicalsociety.museum",
"historichouses.museum",
"historisch.museum",
"historisches.museum",
"history.museum",
"historyofscience.museum",
"horology.museum",
"house.museum",
"humanities.museum",
"illustration.museum",
"imageandsound.museum",
"indian.museum",
"indiana.museum",
"indianapolis.museum",
"indianmarket.museum",
"intelligence.museum",
"interactive.museum",
"iraq.museum",
"iron.museum",
"isleofman.museum",
"jamison.museum",
"jefferson.museum",
"jerusalem.museum",
"jewelry.museum",
"jewish.museum",
"jewishart.museum",
"jfk.museum",
"journalism.museum",
"judaica.museum",
"judygarland.museum",
"juedisches.museum",
"juif.museum",
"karate.museum",
"karikatur.museum",
"kids.museum",
"koebenhavn.museum",
"koeln.museum",
"kunst.museum",
"kunstsammlung.museum",
"kunstunddesign.museum",
"labor.museum",
"labour.museum",
"lajolla.museum",
"lancashire.museum",
"landes.museum",
"lans.museum",
"läns.museum",
"larsson.museum",
"lewismiller.museum",
"lincoln.museum",
"linz.museum",
"living.museum",
"livinghistory.museum",
"localhistory.museum",
"london.museum",
"losangeles.museum",
"louvre.museum",
"loyalist.museum",
"lucerne.museum",
"luxembourg.museum",
"luzern.museum",
"mad.museum",
"madrid.museum",
"mallorca.museum",
"manchester.museum",
"mansion.museum",
"mansions.museum",
"manx.museum",
"marburg.museum",
"maritime.museum",
"maritimo.museum",
"maryland.museum",
"marylhurst.museum",
"media.museum",
"medical.museum",
"medizinhistorisches.museum",
"meeres.museum",
"memorial.museum",
"mesaverde.museum",
"michigan.museum",
"midatlantic.museum",
"military.museum",
"mill.museum",
"miners.museum",
"mining.museum",
"minnesota.museum",
"missile.museum",
"missoula.museum",
"modern.museum",
"moma.museum",
"money.museum",
"monmouth.museum",
"monticello.museum",
"montreal.museum",
"moscow.museum",
"motorcycle.museum",
"muenchen.museum",
"muenster.museum",
"mulhouse.museum",
"muncie.museum",
"museet.museum",
"museumcenter.museum",
"museumvereniging.museum",
"music.museum",
"national.museum",
"nationalfirearms.museum",
"nationalheritage.museum",
"nativeamerican.museum",
"naturalhistory.museum",
"naturalhistorymuseum.museum",
"naturalsciences.museum",
"nature.museum",
"naturhistorisches.museum",
"natuurwetenschappen.museum",
"naumburg.museum",
"naval.museum",
"nebraska.museum",
"neues.museum",
"newhampshire.museum",
"newjersey.museum",
"newmexico.museum",
"newport.museum",
"newspaper.museum",
"newyork.museum",
"niepce.museum",
"norfolk.museum",
"north.museum",
"nrw.museum",
"nuernberg.museum",
"nuremberg.museum",
"nyc.museum",
"nyny.museum",
"oceanographic.museum",
"oceanographique.museum",
"omaha.museum",
"online.museum",
"ontario.museum",
"openair.museum",
"oregon.museum",
"oregontrail.museum",
"otago.museum",
"oxford.museum",
"pacific.museum",
"paderborn.museum",
"palace.museum",
"paleo.museum",
"palmsprings.museum",
"panama.museum",
"paris.museum",
"pasadena.museum",
"pharmacy.museum",
"philadelphia.museum",
"philadelphiaarea.museum",
"philately.museum",
"phoenix.museum",
"photography.museum",
"pilots.museum",
"pittsburgh.museum",
"planetarium.museum",
"plantation.museum",
"plants.museum",
"plaza.museum",
"portal.museum",
"portland.museum",
"portlligat.museum",
"posts-and-telecommunications.museum",
"preservation.museum",
"presidio.museum",
"press.museum",
"project.museum",
"public.museum",
"pubol.museum",
"quebec.museum",
"railroad.museum",
"railway.museum",
"research.museum",
"resistance.museum",
"riodejaneiro.museum",
"rochester.museum",
"rockart.museum",
"roma.museum",
"russia.museum",
"saintlouis.museum",
"salem.museum",
"salvadordali.museum",
"salzburg.museum",
"sandiego.museum",
"sanfrancisco.museum",
"santabarbara.museum",
"santacruz.museum",
"santafe.museum",
"saskatchewan.museum",
"satx.museum",
"savannahga.museum",
"schlesisches.museum",
"schoenbrunn.museum",
"schokoladen.museum",
"school.museum",
"schweiz.museum",
"science.museum",
"scienceandhistory.museum",
"scienceandindustry.museum",
"sciencecenter.museum",
"sciencecenters.museum",
"science-fiction.museum",
"sciencehistory.museum",
"sciences.museum",
"sciencesnaturelles.museum",
"scotland.museum",
"seaport.museum",
"settlement.museum",
"settlers.museum",
"shell.museum",
"sherbrooke.museum",
"sibenik.museum",
"silk.museum",
"ski.museum",
"skole.museum",
"society.museum",
"sologne.museum",
"soundandvision.museum",
"southcarolina.museum",
"southwest.museum",
"space.museum",
"spy.museum",
"square.museum",
"stadt.museum",
"stalbans.museum",
"starnberg.museum",
"state.museum",
"stateofdelaware.museum",
"station.museum",
"steam.museum",
"steiermark.museum",
"stjohn.museum",
"stockholm.museum",
"stpetersburg.museum",
"stuttgart.museum",
"suisse.museum",
"surgeonshall.museum",
"surrey.museum",
"svizzera.museum",
"sweden.museum",
"sydney.museum",
"tank.museum",
"tcm.museum",
"technology.museum",
"telekommunikation.museum",
"television.museum",
"texas.museum",
"textile.museum",
"theater.museum",
"time.museum",
"timekeeping.museum",
"topology.museum",
"torino.museum",
"touch.museum",
"town.museum",
"transport.museum",
"tree.museum",
"trolley.museum",
"trust.museum",
"trustee.museum",
"uhren.museum",
"ulm.museum",
"undersea.museum",
"university.museum",
"usa.museum",
"usantiques.museum",
"usarts.museum",
"uscountryestate.museum",
"usculture.museum",
"usdecorativearts.museum",
"usgarden.museum",
"ushistory.museum",
"ushuaia.museum",
"uslivinghistory.museum",
"utah.museum",
"uvic.museum",
"valley.museum",
"vantaa.museum",
"versailles.museum",
"viking.museum",
"village.museum",
"virginia.museum",
"virtual.museum",
"virtuel.museum",
"vlaanderen.museum",
"volkenkunde.museum",
"wales.museum",
"wallonie.museum",
"war.museum",
"washingtondc.museum",
"watchandclock.museum",
"watch-and-clock.museum",
"western.museum",
"westfalen.museum",
"whaling.museum",
"wildlife.museum",
"williamsburg.museum",
"windmill.museum",
"workshop.museum",
"york.museum",
"yorkshire.museum",
"yosemite.museum",
"youth.museum",
"zoological.museum",
"zoology.museum",
"ירושלים.museum",
"иком.museum",
"mv",
"aero.mv",
"biz.mv",
"com.mv",
"coop.mv",
"edu.mv",
"gov.mv",
"info.mv",
"int.mv",
"mil.mv",
"museum.mv",
"name.mv",
"net.mv",
"org.mv",
"pro.mv",
"mw",
"ac.mw",
"biz.mw",
"co.mw",
"com.mw",
"coop.mw",
"edu.mw",
"gov.mw",
"int.mw",
"museum.mw",
"net.mw",
"org.mw",
"mx",
"com.mx",
"org.mx",
"gob.mx",
"edu.mx",
"net.mx",
"my",
"com.my",
"net.my",
"org.my",
"gov.my",
"edu.my",
"mil.my",
"name.my",
"*.mz",
"na",
"info.na",
"pro.na",
"name.na",
"school.na",
"or.na",
"dr.na",
"us.na",
"mx.na",
"ca.na",
"in.na",
"cc.na",
"tv.na",
"ws.na",
"mobi.na",
"co.na",
"com.na",
"org.na",
"name",
"nc",
"asso.nc",
"ne",
"net",
"gb.net",
"se.net",
"uk.net",
"za.net",
"nf",
"com.nf",
"net.nf",
"per.nf",
"rec.nf",
"web.nf",
"arts.nf",
"firm.nf",
"info.nf",
"other.nf",
"store.nf",
"ac.ng",
"com.ng",
"edu.ng",
"gov.ng",
"net.ng",
"org.ng",
"*.ni",
"nl",
"no",
"fhs.no",
"vgs.no",
"fylkesbibl.no",
"folkebibl.no",
"museum.no",
"idrett.no",
"priv.no",
"mil.no",
"stat.no",
"dep.no",
"kommune.no",
"herad.no",
"aa.no",
"ah.no",
"bu.no",
"fm.no",
"hl.no",
"hm.no",
"jan-mayen.no",
"mr.no",
"nl.no",
"nt.no",
"of.no",
"ol.no",
"oslo.no",
"rl.no",
"sf.no",
"st.no",
"svalbard.no",
"tm.no",
"tr.no",
"va.no",
"vf.no",
"gs.aa.no",
"gs.ah.no",
"gs.bu.no",
"gs.fm.no",
"gs.hl.no",
"gs.hm.no",
"gs.jan-mayen.no",
"gs.mr.no",
"gs.nl.no",
"gs.nt.no",
"gs.of.no",
"gs.ol.no",
"gs.oslo.no",
"gs.rl.no",
"gs.sf.no",
"gs.st.no",
"gs.svalbard.no",
"gs.tm.no",
"gs.tr.no",
"gs.va.no",
"gs.vf.no",
"akrehamn.no",
"åkrehamn.no",
"algard.no",
"ålgård.no",
"arna.no",
"brumunddal.no",
"bryne.no",
"bronnoysund.no",
"brønnøysund.no",
"drobak.no",
"drøbak.no",
"egersund.no",
"fetsund.no",
"floro.no",
"florø.no",
"fredrikstad.no",
"hokksund.no",
"honefoss.no",
"hønefoss.no",
"jessheim.no",
"jorpeland.no",
"jørpeland.no",
"kirkenes.no",
"kopervik.no",
"krokstadelva.no",
"langevag.no",
"langevåg.no",
"leirvik.no",
"mjondalen.no",
"mjøndalen.no",
"mo-i-rana.no",
"mosjoen.no",
"mosjøen.no",
"nesoddtangen.no",
"orkanger.no",
"osoyro.no",
"osøyro.no",
"raholt.no",
"råholt.no",
"sandnessjoen.no",
"sandnessjøen.no",
"skedsmokorset.no",
"slattum.no",
"spjelkavik.no",
"stathelle.no",
"stavern.no",
"stjordalshalsen.no",
"stjørdalshalsen.no",
"tananger.no",
"tranby.no",
"vossevangen.no",
"afjord.no",
"åfjord.no",
"agdenes.no",
"al.no",
"ål.no",
"alesund.no",
"ålesund.no",
"alstahaug.no",
"alta.no",
"áltá.no",
"alaheadju.no",
"álaheadju.no",
"alvdal.no",
"amli.no",
"åmli.no",
"amot.no",
"åmot.no",
"andebu.no",
"andoy.no",
"andøy.no",
"andasuolo.no",
"ardal.no",
"årdal.no",
"aremark.no",
"arendal.no",
"ås.no",
"aseral.no",
"åseral.no",
"asker.no",
"askim.no",
"askvoll.no",
"askoy.no",
"askøy.no",
"asnes.no",
"åsnes.no",
"audnedaln.no",
"aukra.no",
"aure.no",
"aurland.no",
"aurskog-holand.no",
"aurskog-høland.no",
"austevoll.no",
"austrheim.no",
"averoy.no",
"averøy.no",
"balestrand.no",
"ballangen.no",
"balat.no",
"bálát.no",
"balsfjord.no",
"bahccavuotna.no",
"báhccavuotna.no",
"bamble.no",
"bardu.no",
"beardu.no",
"beiarn.no",
"bajddar.no",
"bájddar.no",
"baidar.no",
"báidár.no",
"berg.no",
"bergen.no",
"berlevag.no",
"berlevåg.no",
"bearalvahki.no",
"bearalváhki.no",
"bindal.no",
"birkenes.no",
"bjarkoy.no",
"bjarkøy.no",
"bjerkreim.no",
"bjugn.no",
"bodo.no",
"bodø.no",
"badaddja.no",
"bådåddjå.no",
"budejju.no",
"bokn.no",
"bremanger.no",
"bronnoy.no",
"brønnøy.no",
"bygland.no",
"bykle.no",
"barum.no",
"bærum.no",
"bo.telemark.no",
"bø.telemark.no",
"bo.nordland.no",
"bø.nordland.no",
"bievat.no",
"bievát.no",
"bomlo.no",
"bømlo.no",
"batsfjord.no",
"båtsfjord.no",
"bahcavuotna.no",
"báhcavuotna.no",
"dovre.no",
"drammen.no",
"drangedal.no",
"dyroy.no",
"dyrøy.no",
"donna.no",
"dønna.no",
"eid.no",
"eidfjord.no",
"eidsberg.no",
"eidskog.no",
"eidsvoll.no",
"eigersund.no",
"elverum.no",
"enebakk.no",
"engerdal.no",
"etne.no",
"etnedal.no",
"evenes.no",
"evenassi.no",
"evenášši.no",
"evje-og-hornnes.no",
"farsund.no",
"fauske.no",
"fuossko.no",
"fuoisku.no",
"fedje.no",
"fet.no",
"finnoy.no",
"finnøy.no",
"fitjar.no",
"fjaler.no",
"fjell.no",
"flakstad.no",
"flatanger.no",
"flekkefjord.no",
"flesberg.no",
"flora.no",
"fla.no",
"flå.no",
"folldal.no",
"forsand.no",
"fosnes.no",
"frei.no",
"frogn.no",
"froland.no",
"frosta.no",
"frana.no",
"fræna.no",
"froya.no",
"frøya.no",
"fusa.no",
"fyresdal.no",
"forde.no",
"førde.no",
"gamvik.no",
"gangaviika.no",
"gáŋgaviika.no",
"gaular.no",
"gausdal.no",
"gildeskal.no",
"gildeskål.no",
"giske.no",
"gjemnes.no",
"gjerdrum.no",
"gjerstad.no",
"gjesdal.no",
"gjovik.no",
"gjøvik.no",
"gloppen.no",
"gol.no",
"gran.no",
"grane.no",
"granvin.no",
"gratangen.no",
"grimstad.no",
"grong.no",
"kraanghke.no",
"kråanghke.no",
"grue.no",
"gulen.no",
"hadsel.no",
"halden.no",
"halsa.no",
"hamar.no",
"hamaroy.no",
"habmer.no",
"hábmer.no",
"hapmir.no",
"hápmir.no",
"hammerfest.no",
"hammarfeasta.no",
"hámmárfeasta.no",
"haram.no",
"hareid.no",
"harstad.no",
"hasvik.no",
"aknoluokta.no",
"ákŋoluokta.no",
"hattfjelldal.no",
"aarborte.no",
"haugesund.no",
"hemne.no",
"hemnes.no",
"hemsedal.no",
"heroy.more-og-romsdal.no",
"herøy.møre-og-romsdal.no",
"heroy.nordland.no",
"herøy.nordland.no",
"hitra.no",
"hjartdal.no",
"hjelmeland.no",
"hobol.no",
"hobøl.no",
"hof.no",
"hol.no",
"hole.no",
"holmestrand.no",
"holtalen.no",
"holtålen.no",
"hornindal.no",
"horten.no",
"hurdal.no",
"hurum.no",
"hvaler.no",
"hyllestad.no",
"hagebostad.no",
"hægebostad.no",
"hoyanger.no",
"høyanger.no",
"hoylandet.no",
"høylandet.no",
"ha.no",
"hå.no",
"ibestad.no",
"inderoy.no",
"inderøy.no",
"iveland.no",
"jevnaker.no",
"jondal.no",
"jolster.no",
"jølster.no",
"karasjok.no",
"karasjohka.no",
"kárášjohka.no",
"karlsoy.no",
"galsa.no",
"gálsá.no",
"karmoy.no",
"karmøy.no",
"kautokeino.no",
"guovdageaidnu.no",
"klepp.no",
"klabu.no",
"klæbu.no",
"kongsberg.no",
"kongsvinger.no",
"kragero.no",
"kragerø.no",
"kristiansand.no",
"kristiansund.no",
"krodsherad.no",
"krødsherad.no",
"kvalsund.no",
"rahkkeravju.no",
"ráhkkerávju.no",
"kvam.no",
"kvinesdal.no",
"kvinnherad.no",
"kviteseid.no",
"kvitsoy.no",
"kvitsøy.no",
"kvafjord.no",
"kvæfjord.no",
"giehtavuoatna.no",
"kvanangen.no",
"kvænangen.no",
"navuotna.no",
"návuotna.no",
"kafjord.no",
"kåfjord.no",
"gaivuotna.no",
"gáivuotna.no",
"larvik.no",
"lavangen.no",
"lavagis.no",
"loabat.no",
"loabát.no",
"lebesby.no",
"davvesiida.no",
"leikanger.no",
"leirfjord.no",
"leka.no",
"leksvik.no",
"lenvik.no",
"leangaviika.no",
"leaŋgaviika.no",
"lesja.no",
"levanger.no",
"lier.no",
"lierne.no",
"lillehammer.no",
"lillesand.no",
"lindesnes.no",
"lindas.no",
"lindås.no",
"lom.no",
"loppa.no",
"lahppi.no",
"láhppi.no",
"lund.no",
"lunner.no",
"luroy.no",
"lurøy.no",
"luster.no",
"lyngdal.no",
"lyngen.no",
"ivgu.no",
"lardal.no",
"lerdal.no",
"lærdal.no",
"lodingen.no",
"lødingen.no",
"lorenskog.no",
"lørenskog.no",
"loten.no",
"løten.no",
"malvik.no",
"masoy.no",
"måsøy.no",
"muosat.no",
"muosát.no",
"mandal.no",
"marker.no",
"marnardal.no",
"masfjorden.no",
"meland.no",
"meldal.no",
"melhus.no",
"meloy.no",
"meløy.no",
"meraker.no",
"meråker.no",
"moareke.no",
"moåreke.no",
"midsund.no",
"midtre-gauldal.no",
"modalen.no",
"modum.no",
"molde.no",
"moskenes.no",
"moss.no",
"mosvik.no",
"malselv.no",
"målselv.no",
"malatvuopmi.no",
"málatvuopmi.no",
"namdalseid.no",
"aejrie.no",
"namsos.no",
"namsskogan.no",
"naamesjevuemie.no",
"nååmesjevuemie.no",
"laakesvuemie.no",
"nannestad.no",
"narvik.no",
"narviika.no",
"naustdal.no",
"nedre-eiker.no",
"nes.akershus.no",
"nes.buskerud.no",
"nesna.no",
"nesodden.no",
"nesseby.no",
"unjarga.no",
"unjárga.no",
"nesset.no",
"nissedal.no",
"nittedal.no",
"nord-aurdal.no",
"nord-fron.no",
"nord-odal.no",
"norddal.no",
"nordkapp.no",
"davvenjarga.no",
"davvenjárga.no",
"nordre-land.no",
"nordreisa.no",
"raisa.no",
"ráisa.no",
"nore-og-uvdal.no",
"notodden.no",
"naroy.no",
"nærøy.no",
"notteroy.no",
"nøtterøy.no",
"odda.no",
"oksnes.no",
"øksnes.no",
"oppdal.no",
"oppegard.no",
"oppegård.no",
"orkdal.no",
"orland.no",
"ørland.no",
"orskog.no",
"ørskog.no",
"orsta.no",
"ørsta.no",
"os.hedmark.no",
"os.hordaland.no",
"osen.no",
"osteroy.no",
"osterøy.no",
"ostre-toten.no",
"østre-toten.no",
"overhalla.no",
"ovre-eiker.no",
"øvre-eiker.no",
"oyer.no",
"øyer.no",
"oygarden.no",
"øygarden.no",
"oystre-slidre.no",
"øystre-slidre.no",
"porsanger.no",
"porsangu.no",
"porsáŋgu.no",
"porsgrunn.no",
"radoy.no",
"radøy.no",
"rakkestad.no",
"rana.no",
"ruovat.no",
"randaberg.no",
"rauma.no",
"rendalen.no",
"rennebu.no",
"rennesoy.no",
"rennesøy.no",
"rindal.no",
"ringebu.no",
"ringerike.no",
"ringsaker.no",
"rissa.no",
"risor.no",
"risør.no",
"roan.no",
"rollag.no",
"rygge.no",
"ralingen.no",
"rælingen.no",
"rodoy.no",
"rødøy.no",
"romskog.no",
"rømskog.no",
"roros.no",
"røros.no",
"rost.no",
"røst.no",
"royken.no",
"røyken.no",
"royrvik.no",
"røyrvik.no",
"rade.no",
"råde.no",
"salangen.no",
"siellak.no",
"saltdal.no",
"salat.no",
"sálát.no",
"sálat.no",
"samnanger.no",
"sande.more-og-romsdal.no",
"sande.møre-og-romsdal.no",
"sande.vestfold.no",
"sandefjord.no",
"sandnes.no",
"sandoy.no",
"sandøy.no",
"sarpsborg.no",
"sauda.no",
"sauherad.no",
"sel.no",
"selbu.no",
"selje.no",
"seljord.no",
"sigdal.no",
"siljan.no",
"sirdal.no",
"skaun.no",
"skedsmo.no",
"ski.no",
"skien.no",
"skiptvet.no",
"skjervoy.no",
"skjervøy.no",
"skierva.no",
"skiervá.no",
"skjak.no",
"skjåk.no",
"skodje.no",
"skanland.no",
"skånland.no",
"skanit.no",
"skánit.no",
"smola.no",
"smøla.no",
"snillfjord.no",
"snasa.no",
"snåsa.no",
"snoasa.no",
"snaase.no",
"snåase.no",
"sogndal.no",
"sokndal.no",
"sola.no",
"solund.no",
"songdalen.no",
"sortland.no",
"spydeberg.no",
"stange.no",
"stavanger.no",
"steigen.no",
"steinkjer.no",
"stjordal.no",
"stjørdal.no",
"stokke.no",
"stor-elvdal.no",
"stord.no",
"stordal.no",
"storfjord.no",
"omasvuotna.no",
"strand.no",
"stranda.no",
"stryn.no",
"sula.no",
"suldal.no",
"sund.no",
"sunndal.no",
"surnadal.no",
"sveio.no",
"svelvik.no",
"sykkylven.no",
"sogne.no",
"søgne.no",
"somna.no",
"sømna.no",
"sondre-land.no",
"søndre-land.no",
"sor-aurdal.no",
"sør-aurdal.no",
"sor-fron.no",
"sør-fron.no",
"sor-odal.no",
"sør-odal.no",
"sor-varanger.no",
"sør-varanger.no",
"matta-varjjat.no",
"mátta-várjjat.no",
"sorfold.no",
"sørfold.no",
"sorreisa.no",
"sørreisa.no",
"sorum.no",
"sørum.no",
"tana.no",
"deatnu.no",
"time.no",
"tingvoll.no",
"tinn.no",
"tjeldsund.no",
"dielddanuorri.no",
"tjome.no",
"tjøme.no",
"tokke.no",
"tolga.no",
"torsken.no",
"tranoy.no",
"tranøy.no",
"tromso.no",
"tromsø.no",
"tromsa.no",
"romsa.no",
"trondheim.no",
"troandin.no",
"trysil.no",
"trana.no",
"træna.no",
"trogstad.no",
"trøgstad.no",
"tvedestrand.no",
"tydal.no",
"tynset.no",
"tysfjord.no",
"divtasvuodna.no",
"divttasvuotna.no",
"tysnes.no",
"tysvar.no",
"tysvær.no",
"tonsberg.no",
"tønsberg.no",
"ullensaker.no",
"ullensvang.no",
"ulvik.no",
"utsira.no",
"vadso.no",
"vadsø.no",
"cahcesuolo.no",
"čáhcesuolo.no",
"vaksdal.no",
"valle.no",
"vang.no",
"vanylven.no",
"vardo.no",
"vardø.no",
"varggat.no",
"várggát.no",
"vefsn.no",
"vaapste.no",
"vega.no",
"vegarshei.no",
"vegårshei.no",
"vennesla.no",
"verdal.no",
"verran.no",
"vestby.no",
"vestnes.no",
"vestre-slidre.no",
"vestre-toten.no",
"vestvagoy.no",
"vestvågøy.no",
"vevelstad.no",
"vik.no",
"vikna.no",
"vindafjord.no",
"volda.no",
"voss.no",
"varoy.no",
"værøy.no",
"vagan.no",
"vågan.no",
"voagat.no",
"vagsoy.no",
"vågsøy.no",
"vaga.no",
"vågå.no",
"valer.ostfold.no",
"våler.østfold.no",
"valer.hedmark.no",
"våler.hedmark.no",
"*.np",
"nr",
"biz.nr",
"info.nr",
"gov.nr",
"edu.nr",
"org.nr",
"net.nr",
"com.nr",
"nu",
"*.nz",
"*.om",
"org",
"ae.org",
"za.org",
"pa",
"ac.pa",
"gob.pa",
"com.pa",
"org.pa",
"sld.pa",
"edu.pa",
"net.pa",
"ing.pa",
"abo.pa",
"med.pa",
"nom.pa",
"pe",
"edu.pe",
"gob.pe",
"nom.pe",
"mil.pe",
"org.pe",
"com.pe",
"net.pe",
"pf",
"com.pf",
"org.pf",
"edu.pf",
"*.pg",
"ph",
"com.ph",
"net.ph",
"org.ph",
"gov.ph",
"edu.ph",
"ngo.ph",
"mil.ph",
"i.ph",
"pk",
"com.pk",
"net.pk",
"edu.pk",
"org.pk",
"fam.pk",
"biz.pk",
"web.pk",
"gov.pk",
"gob.pk",
"gok.pk",
"gon.pk",
"gop.pk",
"gos.pk",
"info.pk",
"pl",
"aid.pl",
"agro.pl",
"atm.pl",
"auto.pl",
"biz.pl",
"com.pl",
"edu.pl",
"gmina.pl",
"gsm.pl",
"info.pl",
"mail.pl",
"miasta.pl",
"media.pl",
"mil.pl",
"net.pl",
"nieruchomosci.pl",
"nom.pl",
"org.pl",
"pc.pl",
"powiat.pl",
"priv.pl",
"realestate.pl",
"rel.pl",
"sex.pl",
"shop.pl",
"sklep.pl",
"sos.pl",
"szkola.pl",
"targi.pl",
"tm.pl",
"tourism.pl",
"travel.pl",
"turystyka.pl",
"6bone.pl",
"art.pl",
"mbone.pl",
"gov.pl",
"uw.gov.pl",
"um.gov.pl",
"ug.gov.pl",
"upow.gov.pl",
"starostwo.gov.pl",
"so.gov.pl",
"sr.gov.pl",
"po.gov.pl",
"pa.gov.pl",
"ngo.pl",
"irc.pl",
"usenet.pl",
"augustow.pl",
"babia-gora.pl",
"bedzin.pl",
"beskidy.pl",
"bialowieza.pl",
"bialystok.pl",
"bielawa.pl",
"bieszczady.pl",
"boleslawiec.pl",
"bydgoszcz.pl",
"bytom.pl",
"cieszyn.pl",
"czeladz.pl",
"czest.pl",
"dlugoleka.pl",
"elblag.pl",
"elk.pl",
"glogow.pl",
"gniezno.pl",
"gorlice.pl",
"grajewo.pl",
"ilawa.pl",
"jaworzno.pl",
"jelenia-gora.pl",
"jgora.pl",
"kalisz.pl",
"kazimierz-dolny.pl",
"karpacz.pl",
"kartuzy.pl",
"kaszuby.pl",
"katowice.pl",
"kepno.pl",
"ketrzyn.pl",
"klodzko.pl",
"kobierzyce.pl",
"kolobrzeg.pl",
"konin.pl",
"konskowola.pl",
"kutno.pl",
"lapy.pl",
"lebork.pl",
"legnica.pl",
"lezajsk.pl",
"limanowa.pl",
"lomza.pl",
"lowicz.pl",
"lubin.pl",
"lukow.pl",
"malbork.pl",
"malopolska.pl",
"mazowsze.pl",
"mazury.pl",
"mielec.pl",
"mielno.pl",
"mragowo.pl",
"naklo.pl",
"nowaruda.pl",
"nysa.pl",
"olawa.pl",
"olecko.pl",
"olkusz.pl",
"olsztyn.pl",
"opoczno.pl",
"opole.pl",
"ostroda.pl",
"ostroleka.pl",
"ostrowiec.pl",
"ostrowwlkp.pl",
"pila.pl",
"pisz.pl",
"podhale.pl",
"podlasie.pl",
"polkowice.pl",
"pomorze.pl",
"pomorskie.pl",
"prochowice.pl",
"pruszkow.pl",
"przeworsk.pl",
"pulawy.pl",
"radom.pl",
"rawa-maz.pl",
"rybnik.pl",
"rzeszow.pl",
"sanok.pl",
"sejny.pl",
"siedlce.pl",
"slask.pl",
"slupsk.pl",
"sosnowiec.pl",
"stalowa-wola.pl",
"skoczow.pl",
"starachowice.pl",
"stargard.pl",
"suwalki.pl",
"swidnica.pl",
"swiebodzin.pl",
"swinoujscie.pl",
"szczecin.pl",
"szczytno.pl",
"tarnobrzeg.pl",
"tgory.pl",
"turek.pl",
"tychy.pl",
"ustka.pl",
"walbrzych.pl",
"warmia.pl",
"warszawa.pl",
"waw.pl",
"wegrow.pl",
"wielun.pl",
"wlocl.pl",
"wloclawek.pl",
"wodzislaw.pl",
"wolomin.pl",
"wroclaw.pl",
"zachpomor.pl",
"zagan.pl",
"zarow.pl",
"zgora.pl",
"zgorzelec.pl",
"gda.pl",
"gdansk.pl",
"gdynia.pl",
"med.pl",
"sopot.pl",
"gliwice.pl",
"krakow.pl",
"poznan.pl",
"wroc.pl",
"zakopane.pl",
"pn",
"gov.pn",
"co.pn",
"org.pn",
"edu.pn",
"net.pn",
"pr",
"com.pr",
"net.pr",
"org.pr",
"gov.pr",
"edu.pr",
"isla.pr",
"pro.pr",
"biz.pr",
"info.pr",
"name.pr",
"est.pr",
"prof.pr",
"ac.pr",
"pro",
"aca.pro",
"bar.pro",
"cpa.pro",
"jur.pro",
"law.pro",
"med.pro",
"eng.pro",
"ps",
"edu.ps",
"gov.ps",
"sec.ps",
"plo.ps",
"com.ps",
"org.ps",
"net.ps",
"pt",
"net.pt",
"gov.pt",
"org.pt",
"edu.pt",
"int.pt",
"publ.pt",
"com.pt",
"nome.pt",
"pw",
"co.pw",
"ne.pw",
"or.pw",
"ed.pw",
"go.pw",
"belau.pw",
"*.py",
"*.qa",
"re",
"com.re",
"asso.re",
"nom.re",
"ro",
"com.ro",
"org.ro",
"tm.ro",
"nt.ro",
"nom.ro",
"info.ro",
"rec.ro",
"arts.ro",
"firm.ro",
"store.ro",
"www.ro",
"rs",
"co.rs",
"org.rs",
"edu.rs",
"ac.rs",
"gov.rs",
"in.rs",
"ru",
"ac.ru",
"com.ru",
"edu.ru",
"int.ru",
"net.ru",
"org.ru",
"pp.ru",
"adygeya.ru",
"altai.ru",
"amur.ru",
"arkhangelsk.ru",
"astrakhan.ru",
"bashkiria.ru",
"belgorod.ru",
"bir.ru",
"bryansk.ru",
"buryatia.ru",
"cbg.ru",
"chel.ru",
"chelyabinsk.ru",
"chita.ru",
"chukotka.ru",
"chuvashia.ru",
"dagestan.ru",
"dudinka.ru",
"e-burg.ru",
"grozny.ru",
"irkutsk.ru",
"ivanovo.ru",
"izhevsk.ru",
"jar.ru",
"joshkar-ola.ru",
"kalmykia.ru",
"kaluga.ru",
"kamchatka.ru",
"karelia.ru",
"kazan.ru",
"kchr.ru",
"kemerovo.ru",
"khabarovsk.ru",
"khakassia.ru",
"khv.ru",
"kirov.ru",
"koenig.ru",
"komi.ru",
"kostroma.ru",
"krasnoyarsk.ru",
"kuban.ru",
"kurgan.ru",
"kursk.ru",
"lipetsk.ru",
"magadan.ru",
"mari.ru",
"mari-el.ru",
"marine.ru",
"mordovia.ru",
"mosreg.ru",
"msk.ru",
"murmansk.ru",
"nalchik.ru",
"nnov.ru",
"nov.ru",
"novosibirsk.ru",
"nsk.ru",
"omsk.ru",
"orenburg.ru",
"oryol.ru",
"palana.ru",
"penza.ru",
"perm.ru",
"pskov.ru",
"ptz.ru",
"rnd.ru",
"ryazan.ru",
"sakhalin.ru",
"samara.ru",
"saratov.ru",
"simbirsk.ru",
"smolensk.ru",
"spb.ru",
"stavropol.ru",
"stv.ru",
"surgut.ru",
"tambov.ru",
"tatarstan.ru",
"tom.ru",
"tomsk.ru",
"tsaritsyn.ru",
"tsk.ru",
"tula.ru",
"tuva.ru",
"tver.ru",
"tyumen.ru",
"udm.ru",
"udmurtia.ru",
"ulan-ude.ru",
"vladikavkaz.ru",
"vladimir.ru",
"vladivostok.ru",
"volgograd.ru",
"vologda.ru",
"voronezh.ru",
"vrn.ru",
"vyatka.ru",
"yakutia.ru",
"yamal.ru",
"yaroslavl.ru",
"yekaterinburg.ru",
"yuzhno-sakhalinsk.ru",
"amursk.ru",
"baikal.ru",
"cmw.ru",
"fareast.ru",
"jamal.ru",
"kms.ru",
"k-uralsk.ru",
"kustanai.ru",
"kuzbass.ru",
"magnitka.ru",
"mytis.ru",
"nakhodka.ru",
"nkz.ru",
"norilsk.ru",
"oskol.ru",
"pyatigorsk.ru",
"rubtsovsk.ru",
"snz.ru",
"syzran.ru",
"vdonsk.ru",
"zgrad.ru",
"gov.ru",
"mil.ru",
"test.ru",
"rw",
"gov.rw",
"net.rw",
"edu.rw",
"ac.rw",
"com.rw",
"co.rw",
"int.rw",
"mil.rw",
"gouv.rw",
"com.sa",
"net.sa",
"org.sa",
"gov.sa",
"med.sa",
"pub.sa",
"edu.sa",
"sch.sa",
"sb",
"com.sb",
"edu.sb",
"gov.sb",
"net.sb",
"org.sb",
"sc",
"com.sc",
"gov.sc",
"net.sc",
"org.sc",
"edu.sc",
"sd",
"com.sd",
"net.sd",
"org.sd",
"edu.sd",
"med.sd",
"gov.sd",
"info.sd",
"se",
"a.se",
"ac.se",
"b.se",
"bd.se",
"brand.se",
"c.se",
"d.se",
"e.se",
"f.se",
"fh.se",
"fhsk.se",
"fhv.se",
"g.se",
"h.se",
"i.se",
"k.se",
"komforb.se",
"kommunalforbund.se",
"komvux.se",
"l.se",
"lanbib.se",
"m.se",
"n.se",
"naturbruksgymn.se",
"o.se",
"org.se",
"p.se",
"parti.se",
"pp.se",
"press.se",
"r.se",
"s.se",
"sshn.se",
"t.se",
"tm.se",
"u.se",
"w.se",
"x.se",
"y.se",
"z.se",
"sg",
"com.sg",
"net.sg",
"org.sg",
"gov.sg",
"edu.sg",
"per.sg",
"sh",
"si",
"sk",
"sl",
"com.sl",
"net.sl",
"edu.sl",
"gov.sl",
"org.sl",
"sm",
"sn",
"art.sn",
"com.sn",
"edu.sn",
"gouv.sn",
"org.sn",
"perso.sn",
"univ.sn",
"sr",
"st",
"co.st",
"com.st",
"consulado.st",
"edu.st",
"embaixada.st",
"gov.st",
"mil.st",
"net.st",
"org.st",
"principe.st",
"saotome.st",
"store.st",
"su",
"*.sv",
"sy",
"edu.sy",
"gov.sy",
"net.sy",
"mil.sy",
"com.sy",
"org.sy",
"sz",
"co.sz",
"ac.sz",
"org.sz",
"tc",
"td",
"tel",
"tf",
"tg",
"th",
"ac.th",
"co.th",
"go.th",
"in.th",
"mi.th",
"net.th",
"or.th",
"tj",
"ac.tj",
"biz.tj",
"co.tj",
"com.tj",
"edu.tj",
"go.tj",
"gov.tj",
"int.tj",
"mil.tj",
"name.tj",
"net.tj",
"nic.tj",
"org.tj",
"test.tj",
"web.tj",
"tk",
"tl",
"gov.tl",
"tm",
"tn",
"com.tn",
"ens.tn",
"fin.tn",
"gov.tn",
"ind.tn",
"intl.tn",
"nat.tn",
"net.tn",
"org.tn",
"info.tn",
"perso.tn",
"tourism.tn",
"edunet.tn",
"rnrt.tn",
"rns.tn",
"rnu.tn",
"mincom.tn",
"agrinet.tn",
"defense.tn",
"turen.tn",
"to",
"com.to",
"gov.to",
"net.to",
"org.to",
"edu.to",
"mil.to",
"*.tr",
"travel",
"tt",
"co.tt",
"com.tt",
"org.tt",
"net.tt",
"biz.tt",
"info.tt",
"pro.tt",
"int.tt",
"coop.tt",
"jobs.tt",
"mobi.tt",
"travel.tt",
"museum.tt",
"aero.tt",
"name.tt",
"gov.tt",
"edu.tt",
"tv",
"com.tv",
"net.tv",
"org.tv",
"gov.tv",
"tw",
"edu.tw",
"gov.tw",
"mil.tw",
"com.tw",
"net.tw",
"org.tw",
"idv.tw",
"game.tw",
"ebiz.tw",
"club.tw",
"網路.tw",
"組織.tw",
"商業.tw",
"ac.tz",
"co.tz",
"go.tz",
"ne.tz",
"or.tz",
"ua",
"com.ua",
"edu.ua",
"gov.ua",
"in.ua",
"net.ua",
"org.ua",
"cherkassy.ua",
"chernigov.ua",
"chernovtsy.ua",
"ck.ua",
"cn.ua",
"crimea.ua",
"cv.ua",
"dn.ua",
"dnepropetrovsk.ua",
"donetsk.ua",
"dp.ua",
"if.ua",
"ivano-frankivsk.ua",
"kh.ua",
"kharkov.ua",
"kherson.ua",
"khmelnitskiy.ua",
"kiev.ua",
"kirovograd.ua",
"km.ua",
"kr.ua",
"ks.ua",
"kv.ua",
"lg.ua",
"lugansk.ua",
"lutsk.ua",
"lviv.ua",
"mk.ua",
"nikolaev.ua",
"od.ua",
"odessa.ua",
"pl.ua",
"poltava.ua",
"rovno.ua",
"rv.ua",
"sebastopol.ua",
"sumy.ua",
"te.ua",
"ternopil.ua",
"uzhgorod.ua",
"vinnica.ua",
"vn.ua",
"zaporizhzhe.ua",
"zp.ua",
"zhitomir.ua",
"zt.ua",
"ug",
"co.ug",
"ac.ug",
"sc.ug",
"go.ug",
"ne.ug",
"or.ug",
"*.uk",
"*.sch.uk",
"!bl.uk",
"!british-library.uk",
"!icnet.uk",
"!jet.uk",
"!nel.uk",
"!nhs.uk",
"!nls.uk",
"!national-library-scotland.uk",
"!parliament.uk",
"us",
"dni.us",
"fed.us",
"isa.us",
"kids.us",
"nsn.us",
"ak.us",
"al.us",
"ar.us",
"as.us",
"az.us",
"ca.us",
"co.us",
"ct.us",
"dc.us",
"de.us",
"fl.us",
"ga.us",
"gu.us",
"hi.us",
"ia.us",
"id.us",
"il.us",
"in.us",
"ks.us",
"ky.us",
"la.us",
"ma.us",
"md.us",
"me.us",
"mi.us",
"mn.us",
"mo.us",
"ms.us",
"mt.us",
"nc.us",
"nd.us",
"ne.us",
"nh.us",
"nj.us",
"nm.us",
"nv.us",
"ny.us",
"oh.us",
"ok.us",
"or.us",
"pa.us",
"pr.us",
"ri.us",
"sc.us",
"sd.us",
"tn.us",
"tx.us",
"ut.us",
"vi.us",
"vt.us",
"va.us",
"wa.us",
"wi.us",
"wv.us",
"wy.us",
"*.uy",
"uz",
"com.uz",
"co.uz",
"va",
"vc",
"com.vc",
"net.vc",
"org.vc",
"gov.vc",
"mil.vc",
"edu.vc",
"*.ve",
"vg",
"vi",
"co.vi",
"com.vi",
"k12.vi",
"net.vi",
"org.vi",
"vn",
"com.vn",
"net.vn",
"org.vn",
"edu.vn",
"gov.vn",
"int.vn",
"ac.vn",
"biz.vn",
"info.vn",
"name.vn",
"pro.vn",
"health.vn",
"vu",
"ws",
"com.ws",
"net.ws",
"org.ws",
"gov.ws",
"edu.ws",
"*.ye",
"*.yu",
"*.za",
"*.zm",
"*.zw",))

def get_domain(fqdn):
    domain_elements = fqdn.split('.')
    try:
        if len(domain_elements) == 4 and \
           all([0 <= int(i) < 256 for i in domain_elements ]) :
           # this is an IP address, return it
           return fqdn
    except ValueError:
        # not an IP address, go on
        pass
    for c in range(-len(domain_elements), 0):
        potential_domain = ".".join(domain_elements[c:])
        potential_wildcard_domain = ".".join(["*"]+domain_elements[c:][1:])
        potential_exception_domain = "!" + potential_domain
        if (potential_exception_domain in tld):
            return ".".join(domain_elements[c:])
        if potential_domain in tld or potential_wildcard_domain in tld:
            return ".".join(domain_elements[c-1:])
    # couldn't find any matching TLD, maybe it's an internal domain ?
    if len(domain_elements) > 2:
        return ".".join(domain_elements[1:])
    return fqdn            

########NEW FILE########
__FILENAME__ = iso8601_parser
# -*- coding: utf-8 -*-

# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

""""""

import dateutil.parser as dp

def iso_to_utc(date):
    """
    @param date: an str datetime instance
    @return: naive datetime set to UTC
    """
    return dp.parse(date)
########NEW FILE########
__FILENAME__ = robots
# -*- coding: utf-8 -*-

# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""In this module we define a regular expression used to fetch the most common
robots."""

import re

# taken from genrobotlist.pl in the awstats project : http://awstats.cvs.sourceforge.net
robots = [
    'antibot',
    'appie',
    'architext',
    'bingbot',
    'bjaaland',
    'digout4u',
    'echo',
    'fast-webcrawler',
    'ferret',
    'googlebot',
    'gulliver',
    'harvest',
    'htdig',
    'ia_archiver',
    'askjeeves',
    'jennybot',
    'linkwalker',
    'lycos',
    'mercator',
    'moget',
    'muscatferret',
    'myweb',
    'netcraft',
    'nomad',
    'petersnews',
    'scooter',
    'slurp',
    'unlost_web_crawler',
    'voila',
    'voyager',
    'webbase',
    'weblayers',
    'wisenutbot',
    'aport',
    'awbot',
    'baiduspider',
    'bobby',
    'boris',
    'bumblebee',
    'cscrawler',
    'daviesbot',
    'exactseek',
    'ezresult',
    'gigabot',
    'gnodspider',
    'grub',
    'henrythemiragorobot',
    'holmes',
    'internetseer',
    'justview',
    'linkbot',
    'metager-linkchecker',
    'linkchecker',
    'microsoft_url_control',
    'msiecrawler',
    'nagios',
    'perman',
    'pompos',
    'rambler',
    'redalert',
    'shoutcast',
    'slysearch',
    'surveybot',
    'turnitinbot',
    'turtlescanner',
    'turtle',
    'ultraseek',
    'webclipping.com',
    'webcompass',
    'yahoo-verticalcrawler',
    'yandex',
    'zealbot',
    'zyborg',
]
robot_regex = re.compile("|".join(robots), re.IGNORECASE)

########NEW FILE########
__FILENAME__ = timezone
# -*- coding: utf-8 -*-

# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

""""""

import pytz

def to_naive_utc(date, from_tz):
    """
    @param date: a naive datetime instance
    @param from_tz: timezone information about the naive datetime
    @return: naive datetime set to UTC
    """
    date = date.replace(tzinfo=None)
    try:
        timezone = pytz.timezone(from_tz)
    except pytz.UnknownTimeZoneError:
        timezone = pytz.utc
    loc_date = timezone.localize(date)
    return loc_date.astimezone(pytz.utc).replace(tzinfo=None)

########NEW FILE########
__FILENAME__ = windows
# -*- coding: utf-8 -*-

# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2012 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""Windows and MS-related utility functions."""

from datetime import datetime

def winUTC2UnixTimestamp(winTimestamp):
	"""Converts a windows UTC timestamp (increments of 100 nanoseconds since Jan 1, 1601)
	into a Unix EPOCH timestamp.
	
	@param winTimestamp : the windows timestamp"""
	
	a = int(winTimestamp)
	unixts = (a / 10000000) - 11644473600
	return datetime.fromtimestamp(unixts).isoformat()

########NEW FILE########
__FILENAME__ = lognormalizer
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#


"""This module exposes the L{LogNormalizer} class that can be used for
higher-level management of the normalization flow.
Using this module is in no way mandatory in order to benefit from
the normalization system; the C{LogNormalizer} class provides basic facilities
for further integration in a wider project (web services, ...).
"""

import os
import uuid as _UUID_
import warnings
import StringIO

from normalizer import Normalizer
from lxml.etree import parse, DTD, fromstring as XMLfromstring

class LogNormalizer():
    """Basic normalization flow manager.
    Normalizers definitions are loaded from a path and checked against the DTD.
    If the definitions are syntactically correct, the normalizers are
    instantiated and populate the manager's cache.
    Normalization priormority is established as follows:
    
    * Maximum priority assigned to normalizers where the "appliedTo" tag is set
      to "raw". They MUST be mutually exclusive.
    * Medium priority assigned to normalizers where the "appliedTo" tag is set
      to "body".
    * Lowest priority assigned to any remaining normalizers.
    
    Some extra treatment is also done prior and after the log normalization:
    
    * Assignment of a unique ID, under the tag "uuid"
    * Conversion of date tags to UTC, if the "_timezone" was set prior to
      the normalization process."""
    
    def __init__(self, normalizers_paths, active_normalizers = {}):
        """
        Instantiates a flow manager. The default behavior is to activate every
        available normalizer.
        
        @param normalizers_paths: a list of absolute paths to the normalizer
        XML definitions to use or a just a single path as str.
        @param active_normalizers: a dictionary of active normalizers
        in the form {name-version : [True|False]}.
        """
        if not isinstance(normalizers_paths, list or tuple):
            normalizers_paths = [normalizers_paths,]
        self.normalizers_paths = normalizers_paths
        self.active_normalizers = active_normalizers
        self.dtd, self.ctt, self.ccb = None, None, None
        
        # Walk through paths for normalizer.dtd and common_tagTypes.xml
        # /!\ dtd file and common elements will be overrriden if present in
        # many directories.
        for norm_path in self.normalizers_paths:
            if not os.path.isdir(norm_path):
                raise ValueError, "Invalid normalizer directory : %s" % norm_path
            dtd = os.path.join(norm_path, 'normalizer.dtd')
            ctt = os.path.join(norm_path, 'common_tagTypes.xml')
            ccb = os.path.join(norm_path, 'common_callBacks.xml')
            if os.path.isfile(dtd):
                self.dtd = DTD(open(dtd))
            if os.path.isfile(ctt):
                self.ctt = ctt
            if os.path.isfile(ccb):
                self.ccb = ccb
        # Technically the common elements files should NOT be mandatory.
        # But many normalizers use them, so better safe than sorry.
        if not self.dtd or not self.ctt or not self.ccb:
            raise StandardError, "Missing DTD or common library files"
        self._cache = []
        self.reload()
        
    def reload(self):
        """Refreshes this instance's normalizers pool."""
        self.normalizers = { 'raw' : [], 'body' : [] }
        for path in self.iter_normalizer():
            norm = parse(open(path))
            if not self.dtd.validate(norm):
                warnings.warn('Skipping %s : invalid DTD' % path)
                print 'invalid normalizer ', path
            else:
                normalizer = Normalizer(norm, self.ctt, self.ccb)
                normalizer.uuid = self._compute_norm_uuid(normalizer)
                self.normalizers.setdefault(normalizer.appliedTo, [])
                self.normalizers[normalizer.appliedTo].append(normalizer)
        self.activate_normalizers()

    def _compute_norm_uuid(self, normalizer):
        return "%s-%s" % (normalizer.name, normalizer.version)

    def iter_normalizer(self):
        """ Iterates through normalizers and returns the normalizers' paths.
        
        @return: a generator of absolute paths.
        """
        for path in self.normalizers_paths:
            for root, dirs, files in os.walk(path):
                for name in files:
                    if not name.startswith('common_tagTypes') and \
                       not name.startswith('common_callBacks') and \
                           name.endswith('.xml'):
                        yield os.path.join(root, name)

    def __len__(self):
        """ Returns the amount of available normalizers.
        """
        return len([n for n in self.iter_normalizer()])

    def update_normalizer(self, raw_xml_contents, name = None, dir_path = None ):
        """used to add or update a normalizer.
        @param raw_xml_contents: XML description of normalizer as flat XML. It
        must comply to the DTD.
        @param name: if set, the XML description will be saved as name.xml.
        If left blank, name will be fetched from the XML description.
        @param dir_path: the path to the directory where to copy the given
        normalizer.
        """
        path = self.normalizers_paths[0]
        if dir_path:
            if dir_path in self.normalizers_paths:
                path = dir_path
        xmlconf = XMLfromstring(raw_xml_contents).getroottree()
        if not self.dtd.validate(xmlconf):
            raise ValueError, "This definition file does not follow the normalizers DTD :\n\n%s" % \
                               self.dtd.error_log.filter_from_errors()
        if not name:
            name = xmlconf.getroot().get('name')
        if not name.endswith('.xml'):
            name += '.xml'
        xmlconf.write(open(os.path.join(path, name), 'w'),
                      encoding = 'utf8',
                      method = 'xml',
                      pretty_print = True)
        self.reload()

    def get_normalizer_by_uuid(self, uuid):
        """Returns normalizer by uuid."""
        try:
            norm = [ u for u in sum(self.normalizers.values(), []) if u.uuid == uuid][0]
            return norm
        except:
            raise ValueError, "Normalizer uuid : %s not found" % uuid
        
    def get_normalizer_source(self, uuid):
        """Returns the raw XML source of normalizer uuid."""
        return self.get_normalizer_by_uuid(uuid).get_source()
    
    def get_normalizer_path(self, uuid):
        """Returns the filesystem path of a normalizer."""
        return self.get_normalizer_by_uuid(uuid).sys_path

    
    def activate_normalizers(self):
        """Activates normalizers according to what was set by calling
        set_active_normalizers. If no call to the latter function has been
        made so far, this method activates every normalizer."""
        if not self.active_normalizers:
            self.active_normalizers = dict([ (n.uuid, True) for n in \
                        sum([ v for v in self.normalizers.values()], []) ])
        # fool-proof the list
        self.set_active_normalizers(self.active_normalizers)
        # build an ordered cache to speed things up
        self._cache = []
        # First normalizers to apply are the "raw" ones.
        for norm in self.normalizers['raw']:
            # consider the normalizer to be inactive if not
            # explicitly in our list
            if self.active_normalizers.get(norm.uuid, False):
                self._cache.append(norm)
        # Then, apply the applicative normalization on "body":
        for norm in self.normalizers['body']:
            if self.active_normalizers.get(norm.uuid, False):
                self._cache.append(norm)
        # Then, apply everything else
        for norm in sum([ self.normalizers[u] for u in self.normalizers 
                                           if u not in ['raw', 'body']], []):
            if self.active_normalizers.get(norm.uuid, False):
                self._cache.append(norm)

    def get_active_normalizers(self):
        """Returns a dictionary of normalizers; keys are normalizers' uuid and
        values are True|False according to the normalizer's activation state."""
        return self.active_normalizers

    def set_active_normalizers(self, norms = {}):
        """Sets the active/inactive normalizers. Default behavior is to
        deactivate every normalizer.
        
        @param norms: a dictionary, similar to the one returned by
        get_active_normalizers."""
        default = dict([ (n.uuid, False) for n in \
                            sum([ v for v in self.normalizers.values()], []) ])
        default.update(norms)
        self.active_normalizers = default
        
    def lognormalize(self, data):
        """ This method is the entry point to normalize data (a log).

        data is passed through every activated normalizer
        and extra tagging occurs accordingly.
        
        data receives also an extra uuid tag.

        @param data: must be a dictionary with at least a key 'raw' or 'body'
                     with BaseString values (preferably Unicode).
        
        Here an example :
        >>> from logsparser import lognormalizer
        >>> from pprint import pprint
        >>> ln = lognormalizer.LogNormalizer('/usr/local/share/normalizers/')
        >>> mylog = {'raw' : 'Jul 18 15:35:01 zoo /USR/SBIN/CRON[14338]: (root) CMD (/srv/git/redmine-changesets.sh)'}
        >>> ln.lognormalize(mylog)
        >>> pprint mylog
        {'body': '(root) CMD (/srv/git/redmine-changesets.sh)',
        'date': datetime.datetime(2011, 7, 18, 15, 35, 1),
        'pid': '14338',
        'program': '/USR/SBIN/CRON',
        'raw': 'Jul 18 15:35:01 zoo /USR/SBIN/CRON[14338]: (root) CMD (/srv/git/redmine-changesets.sh)',
        'source': 'zoo',
        'uuid': 70851882840934161193887647073096992594L}
        """
        data = self.uuidify(data)
        data = self.normalize(data)

    
    # some more functions for clarity
    def uuidify(self, log):
        """Adds a unique UID to the normalized log."""
        log["uuid"] = _UUID_.uuid4().int
        return log
        
    def normalize(self, log):
        """plain normalization."""
        for norm in self._cache:
            log = norm.normalize(log)
        return log

    def _normalize(self, log):
        """Used for testing only, the normalizers' tags prerequisite are
        deactivated."""
        for norm in self._cache:
            log = norm.normalize(log, do_not_check_prereq = True)
        return log
        

########NEW FILE########
__FILENAME__ = normalizer
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""
Here we have everything needed to parse and use XML definition files.

The only class one should ever use here is L{Normalizer}. The rest is
used during the parsing of the definition files that is taken care of
by the Normalizer class.
"""

import re
import csv
import warnings
import math

from lxml.etree import parse, tostring
from datetime import datetime, timedelta # pyflakes:ignore
import urlparse # pyflakes:ignore
import logsparser.extras as extras # pyflakes:ignore

try:
    import GeoIP #pyflakes:ignore
    country_code_by_address = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE).country_code_by_addr
except ImportError, e:
    country_code_by_address =lambda x: None

# the following symbols and modules are allowed for use in callbacks.
SAFE_SYMBOLS = ["list", "dict", "tuple", "set", "long", "float", "object",
                "bool", "callable", "True", "False", "dir",
                "frozenset", "getattr", "hasattr", "abs", "cmp", "complex",
                "divmod", "id", "pow", "round", "slice", "vars",
                "hash", "hex", "int", "isinstance", "issubclass", "len",
                "map", "filter", "max", "min", "oct", "chr", "ord", "range",
                "reduce", "repr", "str", "unicode", "basestring", "type", "zip",
                "xrange", "None", "Exception", "re", "datetime", "math",
                "urlparse", "country_code_by_address", "extras", "timedelta"]

class Tag(object):
    """A tag as defined in a pattern."""
    def __init__(self,
                 name,
                 tagtype,
                 substitute,
                 description = {},
                 callbacks = []):
        """@param name: the tag's name
        @param tagtype: the tag's type name
        @param substitute: the string chain representing the tag in a log pattern
        @param description = a dictionary holding multilingual descriptions of
        the tag
        @param callbacks: a list of eventual callbacks to fire once the tag value
        has been extracted"""
        self.name = name
        self.tagtype = tagtype
        self.substitute = substitute
        self.description = description
        self.callbacks = callbacks

    def get_description(self, language = 'en'):
        """@Return : The tag description"""
        return self.description.get(language, 'N/A')

class TagType(object):
    """A tag type. This defines how to match a given tag."""
    def __init__(self,
                 name,
                 ttype,
                 regexp,
                 description = {},
                 flags = re.UNICODE | re.IGNORECASE):
        """@param name: the tag type's name
        @param ttype: the expected type of the value fetched by the associated regular expression
        @param regexp: the regular expression (as text, not compiled) associated to this type
        @param description: a dictionary holding multilingual descriptions of
        the tag type
        @param flags: flags by which to compile the regular expression"""
        self.name = name
        self.ttype = ttype
        self.regexp = regexp
        self.description = description
        try:
            self.compiled_regexp = re.compile(regexp, flags)
        except:
            raise ValueError, "Invalid regular expression %s" % regexp
            

# import the common tag types
def get_generic_tagTypes(path = 'normalizers/common_tagTypes.xml'):
    """Imports the common tag types.
    
    @return: a dictionary of tag types."""
    generic = {}
    try:
        tagTypes = parse(open(path, 'r')).getroot()
        for tagType in tagTypes:
            tt_name = tagType.get('name')
            tt_type = tagType.get('ttype') or 'basestring'
            tt_desc = {}
            for child in tagType:
                if child.tag == 'description':
                    for desc in child:
                        lang = desc.get('language') or 'en'
                        tt_desc[lang] = child.text
                elif child.tag == 'regexp':
                    tt_regexp = child.text
            generic[tt_name] = TagType(tt_name, tt_type, tt_regexp, tt_desc)
        return generic
    except StandardError, err:
        warnings.warn("Could not load generic tags definition file : %s \
                       - generic tags will not be available." % err)
        return {}

# import the common callbacks
def get_generic_callBacks(path = 'normalizers/common_callBacks.xml'):
    """Imports the common callbacks.

    @return a dictionnary of callbacks."""
    generic = {}
    try:
        callBacks = parse(open(path, 'r')).getroot()
        for callBack in callBacks:
            cb_name = callBack.get('name')
            # cb_desc = {}
            for child in callBack:
                if child.tag == 'code':
                    cb_code = child.text
		# descriptions are not used yet but implemented in xml and dtd files for later use
                # elif child.tag == 'description':
                #     for desc in child:
                #         lang = desc.get('language')
                #         cb_desc[lang] = desc.text
            generic[cb_name] = CallbackFunction(cb_code, cb_name)
        return generic
    except StandardError, err:
        warnings.warn("Could not load generic callbacks definition file : %s \
                       - generic callbacks will not be available." % err)
        return {}

class PatternExample(object):
    """Represents an log sample matching a given pattern. expected_tags is a
    dictionary of tag names -> values that should be obtained after the
    normalization of this sample."""
    def __init__(self,
                 raw_line,
                 expected_tags = {},
                 description = {}):
        self.raw_line = raw_line
        self.expected_tags = expected_tags
        self.description = description
        
    def get_description(self, language = 'en'):
        """@return : An example description"""
        return { 'sample' : self.raw_line,
                 'normalization' : self.expected_tags }

class Pattern(object):
    """A pattern, as defined in a normalizer configuration file."""
    def __init__(self,
                 name,
                 pattern,
                 tags = {},
                 description = '',
                 commonTags = {},
                 examples = [] ):
        self.name = name
        self.pattern = pattern
        self.tags = tags
        self.description = description
        self.examples = examples
        self.commonTags = commonTags
        
    def normalize(self, logline):
        raise NotImplementedError
        
    def test_examples(self):
        raise NotImplementedError
        
    def get_description(self, language = 'en'):
        tags_desc = dict([ (tag.name, tag.get_description(language)) for tag in self.tags.values() ])
        substitutes = dict([ (tag.substitute, tag.name) for tag in self.tags.values() ])
        examples_desc = [ example.get_description(language) for example in self.examples ]
        return { 'pattern' : self.pattern, 
                 'description' : self.description.get(language, "N/A"),
                 'tags' : tags_desc,
                 'substitutes' : substitutes,
                 'commonTags' : self.commonTags,
                 'examples' : examples_desc }

class CSVPattern(object):
    """A pattern that handle CSV case."""
    def __init__(self,
                 name,
                 pattern,
                 separator = ',',
                 quotechar = '"',
                 tags = {},
                 callBacks = [],
                 tagTypes = {},
                 genericTagTypes = {},
                 genericCallBacks = {},
                 description = '',
                 commonTags = {},
                 examples = []):
        """ 
        @param name: the pattern name
        @param pattern: the CSV pattern
        @param separator: the CSV delimiter
        @param quotechar: the CSV quote character
        @param tags: a dict of L{Tag} instance with Tag name as key
        @param callBacks: a list of L{CallbackFunction}
        @param tagTypes: a dict of L{TagType} instance with TagType name as key
        @param genericTagTypes: a dict of L{TagType} instance from common_tags xml definition with TagType name as key
        @param genericCallBacks: a dict of L{CallBacks} instance from common_callbacks xml definition with callback name as key
        @param description: a pattern description
        @param commonTags: a Dict of tags to add to the final normalisation
        @param examples: a list of L{PatternExample}
        """
        self.name = name
        self.pattern = pattern
        self.separator = separator
        self.quotechar = quotechar
        self.tags = tags
        self.callBacks = callBacks
        self.tagTypes = tagTypes
        self.genericTagTypes = genericTagTypes
        self.genericCallBacks = genericCallBacks
        self.description = description
        self.examples = examples
        self.commonTags = commonTags
        _fields = self.pattern.split(self.separator)
        if self.separator != ' ':
            self.fields = [f.strip() for f in _fields]
        else:
            self.fields = _fields
        self.check_count = len(self.fields)

    def postprocess(self, data):
        for tag in self.tags:
            # tagTypes defined in the conf file take precedence on the
            # generic ones. If nothing found either way, fall back to
            # Anything.
            tag_regexp = self.tagTypes.get(self.tags[tag].tagtype,
                               self.genericTagTypes.get(self.tags[tag].tagtype, self.genericTagTypes['Anything'])).regexp
            r = re.compile(tag_regexp)
            field = self.tags[tag].substitute
            if field not in data.keys():
                continue
            if not r.match(data[field]):
                # We found a tag that not matchs the expected regexp
                return None
            else:
                value = data[field]
                del data[field]
                data[tag] = value
                # try to apply callbacks
                # but do not try to apply callbacks if we do not have any value
                if not data[tag]:
                    continue
                callbacks_names = self.tags[tag].callbacks
                for cbname in callbacks_names:
                    try:
                        # get the callback in the definition file, or look it up in the common library if not found
                        callback = [cb for cb in self.callBacks.values() if cb.name == cbname] or\
                                   [cb for cb in self.genericCallBacks.values() if cb.name == cbname]
                        callback = callback[0]
                    except:
                        warnings.warn("Unable to find callback %s for pattern %s" %
                                     (cbname, self.name))
                        continue
                    try:
                        callback(data[tag], data)
                    except Exception, e:
                        raise Exception("Error on callback %s in pattern %s : %s - skipping" %
                                       (cbname,
                                        self.name, e))
        # remove temporary tags
        temp_tags = [t for t in data.keys() if t.startswith('__')]
        for t in temp_tags:
            del data[t]
        empty_tags = [t for t in data.keys() if not data[t]]
        # remove empty tags
        for t in empty_tags:
            del data[t]
        return data

    def normalize(self, logline):
        # Verify logline is a basestring
        if not isinstance(logline, basestring):
            return None
        # Try to retreive some fields with csv reader
        try:
            data = [data for data in csv.reader([logline], delimiter = self.separator, quotechar = self.quotechar)][0]
        except:
            return None
        # Check we have something in data
        if not data:
            return None
        else:
            # Verify csv reader has match the expected number of fields
            if len(data) != self.check_count:
                return None
            # Check expected for for fileds and apply callbacks
            data = self.postprocess(dict(zip(self.fields, data)))
            # Add common tags
            if data:
                data.update(self.commonTags)
        return data
        
    def test_examples(self):
        raise NotImplementedError
        
    def get_description(self, language = 'en'):
        tags_desc = dict([ (tag.name, tag.get_description(language)) for tag in self.tags.values() ])
        substitutes = dict([ (tag.substitute, tag.name) for tag in self.tags.values() ])
        examples_desc = [ example.get_description(language) for example in self.examples ]
        return { 'pattern' : self.pattern, 
                 'description' : self.description.get(language, "N/A"),
                 'tags' : tags_desc,
                 'substitutes' : substitutes,
                 'commonTags' : self.commonTags,
                 'examples' : examples_desc }

class CallbackFunction(object):
    """This class is used to define a callback function from source code present
    in the XML configuration file. The function is defined in a sanitized
    environment (imports are disabled, for instance).
    This class is inspired from this recipe :
    http://code.activestate.com/recipes/550804-create-a-restricted-python-function-from-a-string/
    """
    def __init__(self, function_body = "log['test'] = value",
                 name = 'unknown'):
        
        source = "def __cbfunc__(value,log):\n"
        source += '\t' + '\n\t'.join(function_body.split('\n')) + '\n'
        
        self.__doc__ = "Callback function generated from the following code:\n\n" + source
        byteCode = compile(source, '<string>', 'exec')
        self.name = name
        
        # Setup a standard-compatible python environment
        builtins   = dict()
        globs      = dict()
        locs       = dict()
        builtins["locals"]  = lambda: locs
        builtins["globals"] = lambda: globs
        globs["__builtins__"] = builtins
        globs["__name__"] = "SAFE_ENV"
        globs["__doc__"] = source
        
        if type(__builtins__) is dict:
            bi_dict = __builtins__
        else:
            bi_dict = __builtins__.__dict__
        
        for k in SAFE_SYMBOLS:
            try:
                locs[k] = locals()[k]
                continue
            except KeyError:
                pass
            try:
                globs[k] = globals()[k]
                continue
            except KeyError:
                pass
            try:
                builtins[k] = bi_dict[k]
            except KeyError:
                pass
        
        # set the function in the safe environment
        eval(byteCode, globs, locs)
        self.cbfunction = locs["__cbfunc__"]
    
    def __call__(self, value, log):
        """call the instance as a function to run the callback."""
        # Exceptions are caught higher up in the normalization process.
        self.cbfunction(value, log)
        return log


class Normalizer(object):
    """Log Normalizer, based on an XML definition file."""
    
    def __init__(self, xmlconf, genericTagTypes, genericCallBacks):
        """initializes the normalizer with an lxml ElementTree.

        @param xmlconf: lxml ElementTree normalizer definition
        @param genericTagTypes: path to generic tags definition xml file
        """
        self.text_source = tostring(xmlconf, pretty_print = True)
        self.sys_path = xmlconf.docinfo.URL
        normalizer = xmlconf.getroot()
        self.genericTagTypes = get_generic_tagTypes(genericTagTypes)
        self.genericCallBacks = get_generic_callBacks(genericCallBacks)
        self.description = {}
        self.authors = []
        self.tagTypes = {}
        self.callbacks = {}
        self.prerequisites = {}
        self.patterns = {}
        self.commonTags = {}
        self.finalCallbacks = []
        self.name = normalizer.get('name')
        self.expandWhitespaces = False
        if not self.name:
            raise ValueError, "The normalizer configuration lacks a name."
        self.version = float(normalizer.get('version')) or 1.0
        self.appliedTo = normalizer.get('appliedTo') or 'raw'
        self.re_flags = ( (normalizer.get('unicode') == "yes" and re.UNICODE ) or 0 ) |\
                        ( (normalizer.get('ignorecase') == "yes" and re.IGNORECASE ) or 0 ) |\
                        ( (normalizer.get('multiline') == "yes" and re.MULTILINE ) or 0 )
        self.matchtype = ( normalizer.get('matchtype') == "search" and "search" ) or 'match'
        self.expandWhitespaces = normalizer.get("expandWhitespaces") == "yes"
        try:
            self.taxonomy = normalizer.get('taxonomy')
        except:
            self.taxonomy = None

        for node in normalizer:
            if node.tag == "description":
                for desc in node:
                    self.description[desc.get('language')] = desc.text
            elif node.tag == "authors":
                for author in node:
                    self.authors.append(author.text)
            elif node.tag == "tagTypes":
                for tagType in node:
                    tT_description = {}
                    tT_regexp = ''
                    for child in tagType:
                        if child.tag == 'description':
                            for desc in child:
                                tT_description[desc.get("language")] = desc.text
                        elif child.tag == 'regexp':
                            tT_regexp = child.text
                    self.tagTypes[tagType.get('name')] = TagType(tagType.get('name'),
                                                                 tagType.get('ttype') or "basestring",
                                                                 tT_regexp,
                                                                 tT_description,
                                                                 self.re_flags)
            elif node.tag == 'callbacks':
                for callback in node:
                    self.callbacks[callback.get('name')] = CallbackFunction(callback.text, callback.get('name'))
            elif node.tag == 'prerequisites':
                for prereqTag in node:
                    self.prerequisites[prereqTag.get('name')] = prereqTag.text
            elif node.tag == 'patterns':
                self.__parse_patterns(node)
            elif node.tag == "commonTags":
                for commonTag in node:
                    self.commonTags[commonTag.get('name')] = commonTag.text
            elif node.tag == "finalCallbacks":
                for callback in node:
                    self.finalCallbacks.append(callback.text)
        # precompile regexp 
        self.full_regexp, self.tags_translation, self.tags_to_pattern, whatever = self.get_uncompiled_regexp()
        self.full_regexp = re.compile(self.full_regexp, self.re_flags)
    
    def __parse_patterns(self, node):
        for pattern in node:
            p_name = pattern.get('name')
            p_description = {}
            p_tags = {}
            p_commonTags = {}
            p_examples = []
            p_csv = {}
            for p_node in pattern:
                if p_node.tag == 'description':
                    for desc in p_node:
                        p_description[desc.get('language')] = desc.text
                elif p_node.tag == 'text':
                    p_pattern = p_node.text
                    if 'type' in p_node.attrib:
                        p_type = p_node.get('type')
                        if p_type == 'csv':
                            p_csv = {'type': 'csv'}
                            if 'separator' in p_node.attrib:
                                p_csv['separator'] = p_node.get('separator')
                            if 'quotechar' in p_node.attrib:
                                p_csv['quotechar'] = p_node.get('quotechar')
                elif p_node.tag == 'tags':
                    for tag in p_node:
                        t_cb = []
                        t_description = {}
                        t_name = tag.get('name')
                        t_tagtype = tag.get('tagType')
                        for child in tag:
                            if child.tag == 'description':
                                for desc in child:
                                    t_description[desc.get('language')] = desc.text
                            if child.tag == 'substitute':
                                t_substitute = child.text
                            elif child.tag == 'callbacks':
                                for cb in child:
                                    t_cb.append(cb.text)
                        p_tags[t_name] = Tag(t_name, t_tagtype, t_substitute, t_description, t_cb) 
                elif p_node.tag == "commonTags":
                    for commontag in p_node:
                        p_commonTags[commontag.get('name')] = commontag.text
                elif p_node.tag == 'examples':
                    for example in p_node:
                        e_description = {}
                        e_expectedTags = {}
                        for child in example:
                            if child.tag == 'description':
                                for desc in child:
                                    e_description[desc.get('language')] = desc.text
                            elif child.tag == 'text':
                                e_rawline = child.text
                            elif child.tag == "expectedTags":
                                for etag in child:
                                    e_expectedTags[etag.get('name')] = etag.text
                        p_examples.append(PatternExample(e_rawline, e_expectedTags, e_description))
            if not p_csv:
                self.patterns[p_name] = Pattern(p_name, p_pattern, p_tags, p_description, p_commonTags, p_examples)
            else:
                self.patterns[p_name] = CSVPattern(p_name, p_pattern, p_csv['separator'], p_csv['quotechar'], p_tags,
                                                   self.callbacks, self.tagTypes, self.genericTagTypes, self.genericCallBacks, p_description,
                                                   p_commonTags, p_examples)

    def get_description(self, language = "en"):
        return "%s v. %s" % (self.name, self.version)
    
    def get_long_description(self, language = 'en'):
        patterns_desc = [ pattern.get_description(language) for pattern in self.patterns.values() ]
        return { 'name' : self.name,
                 'version' : self.version,
                 'authors' : self.authors,
                 'description' : self.description.get(language, "N/A"),
                 'patterns' : patterns_desc,
                 'commonTags' : self.commonTags,
                 'taxonomy' : self.taxonomy }

    def get_uncompiled_regexp(self, p = None, increment = 0):
        """returns the uncompiled regular expression associated to pattern named p.
        If p is None, all patterns are stitched together, ready for compilation.
        increment is the starting value to use for the generic tag names in the
        returned regular expression.
        @return: regexp, dictionary of tag names <-> tag codes,
                 dictionary of tags codes <-> pattern the tag came from,
                 new increment value
        """
        patterns = p
        regexps = []
        tags_translations = {}
        tags_to_pattern = {}
        if not patterns:
            # WARNING ! dictionary keys are not necessarily returned in creation order.
            # This is silly, as the pattern order is crucial. So we must enforce that
            # patterns are named in alphabetical order of precedence ...
            patterns = sorted(self.patterns.keys())
        if isinstance(patterns, basestring):
            patterns = [patterns]
        for pattern in patterns:
            if isinstance(self.patterns[pattern], CSVPattern):
                continue
            regexp = self.patterns[pattern].pattern
            if self.expandWhitespaces:
                regexp = re.sub("\s+", "\s+", regexp)
            for tagname, tag in self.patterns[pattern].tags.items():
                # tagTypes defined in the conf file take precedence on the
                # generic ones. If nothing found either way, fall back to
                # Anything.
                
                tag_regexp = self.tagTypes.get(tag.tagtype, 
                                               self.genericTagTypes.get(tag.tagtype,
                                                                        self.genericTagTypes['Anything'])).regexp
                named_group = '(?P<tag%i>%s)' % (increment, tag_regexp)
                regexp = regexp.replace(tag.substitute, named_group)
                tags_translations['tag%i' % increment] = tagname
                tags_to_pattern['tag%i' % increment] = pattern
                increment += 1
            regexps.append("(?:%s)" % regexp)
        return "|".join(regexps), tags_translations, tags_to_pattern, increment

    def normalize(self, log, do_not_check_prereq = False):
        """normalization in standalone mode.
        @param log: a dictionary or an object providing at least a get() method
        @param do_not_check_prereq: if set to True, the prerequisite tags check
        is skipped (debug purpose only)
        @return: a dictionary with updated tags if normalization was successful."""
        if isinstance(log, basestring) or not hasattr(log, "get"):
            raise ValueError, "the normalizer expects an argument of type Dict"
        # Test prerequisites
        if all( [ re.match(value, log.get(prereq, ''))
                  for prereq, value in self.prerequisites.items() ]) or\
           do_not_check_prereq:
            csv_patterns = [csv_pattern for csv_pattern in self.patterns.values() if isinstance(csv_pattern, CSVPattern)]
            if self.appliedTo in log.keys():
                m = getattr(self.full_regexp, self.matchtype)(log[self.appliedTo])
                if m is not None:
                    m = m.groupdict()
                if m:
                    # this little trick makes the following line not type dependent
                    temp_wl = dict([ (u, log[u]) for u in log.keys() ])
                    for tag in m:
                        if m[tag] is not None:
                            matched_pattern = self.patterns[self.tags_to_pattern[tag]]
                            temp_wl[self.tags_translation[tag]] = m[tag]
                            # apply eventual callbacks
                            for cb in matched_pattern.tags[self.tags_translation[tag]].callbacks:
                                # TODO it could be desirable to make sure the callback
                                # does not try to change important preset values such as
                                # 'raw' and 'uuid'.
                                try:
                                    # if the callback doesn't exist in the normalizer file, it will
                                    # search in the commonCallBack file.
                                    temp_wl = self.callbacks.get(cb, self.genericCallBacks.get(cb))(m[tag], temp_wl)
                                except Exception, e:
                                    pattern_name = self.patterns[self.tags_to_pattern[tag]].name
                                    raise Exception("Error on callback %s in pattern %s : %s - skipping" %
                                                    (self.callbacks[cb].name,
                                                     pattern_name, e))
                            # remove temporary tags
                            if self.tags_translation[tag].startswith('__'):
                                del temp_wl[self.tags_translation[tag]]
                    log.update(temp_wl)
                    # add the pattern's common Tags
                    log.update(matched_pattern.commonTags) 
                    # then add the normalizer's common Tags
                    log.update(self.commonTags)
                    # then add the taxonomy if relevant
                    if self.taxonomy:
                        log['taxonomy'] = self.taxonomy
                    # and finally, apply the final callbacks
                    for cb in self.finalCallbacks:
                        try:
                            log.update(self.callbacks.get(cb, self.genericCallBacks.get(cb))(None, log))
                        except Exception, e:
                            raise Exception("Cannot apply final callback %s : %r - skipping" % (cb, e))
                elif csv_patterns:
                    # this little trick makes the following line not type dependent
                    temp_wl = dict([ (u, log[u]) for u in log.keys() ])
                    ret = None
                    for csv_pattern in csv_patterns:
                        ret = csv_pattern.normalize(temp_wl[self.appliedTo])
                        if ret:
                            log.update(ret)
                            # then add the normalizer's common Tags
                            log.update(self.commonTags)
                            # then add the taxonomy if relevant
                            if self.taxonomy:
                                log['taxonomy'] = self.taxonomy
                            # and finally, apply the final callbacks
                            for cb in self.finalCallbacks:
                                try:
                                    log.update(self.callbacks.get(cb, self.genericCallBacks.get(cb))(None, log))
                                except Exception, e:
                                    raise Exception("Cannot apply final callback %s : %r - skipping" % (cb, e))
                            break
        return log

    def validate(self):
        """if the definition file comes with pattern examples, this method can
        be invoked to test these patterns against the examples.
        Note that tags not included in the "expectedTags" directives will not
        be checked for validation.
        @return: True if the normalizer is validated, raises a ValueError
                 describing the problem otherwise.
        """
        for p in self.patterns:
            for example in self.patterns[p].examples:
                w = { self.appliedTo : example.raw_line }
                if isinstance(self.patterns[p], Pattern):
                    w = self.normalize(w, do_not_check_prereq = True)
                elif isinstance(self.patterns[p], CSVPattern):
                    w = self.patterns[p].normalize(example.raw_line)
                    if w:
                        w.update(self.commonTags)
                        if self.taxonomy:
                            w['taxonomy'] = self.taxonomy
                        for cb in self.finalCallbacks:
                            try:
                                w.update(self.callbacks.get(cb, self.genericCallBacks.get(cb))(None, w))
                            except Exception, e:
                                raise Exception("Cannot apply final callback %s : %r - skipping" % (cb, e))
                for expectedTag in example.expected_tags.keys():
                    if isinstance(w.get(expectedTag), datetime):
                        svalue = str(w.get(expectedTag))
                    elif isinstance(w.get(expectedTag), int):
                        svalue = str(w.get(expectedTag))
                    else:
                        svalue = w.get(expectedTag)
                    if svalue != example.expected_tags[expectedTag]:
                        raise ValueError, 'Sample log "%s" does not match : expected %s -> %s, %s' % \
                                            (example,
                                             expectedTag,
                                             example.expected_tags[expectedTag],
                                             w.get(expectedTag))
        # No problem so far ? Awesome !
        return True

    def get_source(self):
        """gets the raw XML source for this normalizer."""
        return self.text_source
        
    def get_languages(self):
        """guesstimates the available languages from the description field and
        returns them as a list."""
        return self.description.keys()
        
# Documentation generator
def doc2RST(description, gettext = None):
    """ Returns a RestructuredText documentation from
        a parser description.
        @param description: the long description of the parser.
        @param gettext: is the gettext method to use.
                        You must configure gettext to use the domain 'normalizer' and
                        select a language.
                        eg. gettext.translation('normalizer', 'i18n', ['fr_FR']).ugettext
    """
    
    def escape(text):
        if isinstance(text, basestring):
            for c in "*\\":
                text.replace(c, "\\" + c)
        return text

    if not gettext:
        _ = lambda x: x
    else:
        _ = gettext

    template = _("""%(title)s

**Written by**

%(authors)s

Description
:::::::::::

%(description)s %(taxonomy)s

This normalizer can parse logs of the following structure(s):

%(patterns)s

Examples
::::::::

%(examples)s""")

    d = {}
    d['title'] = description['name'] + ' v.' + str(description['version'])
    d['title'] += '\n' + '-'*len(d['title'])
    d['authors'] = '\n'.join( ['* *%s*' % a for a in description['authors'] ] )
    d['description'] = escape(description['description']) or _('undocumented')
    d['taxonomy'] = ''
    if description["taxonomy"]:
        d['taxonomy'] = ("\n\n" +\
                         (_("This normalizer belongs to the category : *%s*") % description['taxonomy']) )
    d['patterns'] = ''
    d['examples'] = ''
    for p in description['patterns']:
        d['patterns'] +="""* %s""" % escape(p['pattern'])
        d['patterns'] += _(", where\n\n")
        for sub in p['substitutes']:
            d['patterns'] += _("  * **%s** is %s ") % (escape(sub), (p['tags'][p['substitutes'][sub]] or _('undocumented') ))
            if not p['substitutes'][sub].startswith('__'):
                d['patterns'] += _("(normalized as *%s*)") % p['substitutes'][sub]
            d['patterns'] += "\n"
        if description['commonTags'] or p['commonTags']:
            d['patterns'] += _("\n  Additionally, The following tags are automatically set:\n\n")
            for name, value in sum([description['commonTags'].items(),
                                    p['commonTags'].items()],
                                   []):
                d['patterns'] += "  * *%s* : %s\n" % (escape(name), value)
            d['patterns'] += "\n"
        if p.get('description') :
            d['patterns'] += "\n  %s\n" % p['description']
        d['patterns'] += "\n"
        for example in p['examples']:
            d['examples'] += _("* *%s*, normalized as\n\n") % escape(example['sample'])
            for tag, value in example['normalization'].items():
                d['examples'] += "  * **%s** -> %s\n" % (escape(tag), value)
            d['examples'] += '\n'
    return template % d


########NEW FILE########
__FILENAME__ = test_commonElements
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

import os
import unittest
from datetime import datetime, timedelta
from logsparser.normalizer import get_generic_tagTypes
from logsparser.normalizer import get_generic_callBacks


def get_sensible_year(*args):
    """args is a list of ordered date elements, from month and day (both 
    mandatory) to eventual second. The function gives the most sensible 
    year for that set of values, so that the date is not set in the future."""
    year = int(datetime.now().year)
    d = datetime(year, *args)
    if d > datetime.now():
        return year - 1
    return year  


def generic_time_callback_test(instance, cb):
    """Testing time formatting callbacks. This is boilerplate code."""
    # so far only time related callbacks were written. If it changes, list
    # here non related functions to skip in this test.
    instance.assertTrue(cb in instance.cb.keys())
    DATES_TO_TEST = [ datetime.utcnow() + timedelta(-1),
                      datetime.utcnow() + timedelta(-180),
                      datetime.utcnow() + timedelta(1), # will always be considered as in the future unless you're testing on new year's eve...
                    ]
    # The pattern translation list. Order is important !
    translations = [ ("YYYY", "%Y"),
                     ("YY"  , "%y"),
                     ("DDD" , "%a"),        # localized day
                     ("DD"  , "%d"),        # day with eventual leading 0
                     ("dd"  , "%d"),        
                     ("MMM" , "%b"),        # localized month
                     ("MM"  , "%m"),        # month number with eventual leading 0
                     ("hh"  , "%H"),
                     ("mm"  , "%M"),
                     ("ss"  , "%S") ]
    pattern = cb
    for old, new in translations:
        pattern = pattern.replace(old, new)
    # special cases
    if pattern == "ISO8601":
        pattern = "%Y-%m-%dT%H:%M:%SZ"
    for d in DATES_TO_TEST:
        if pattern == "EPOCH":
            #value = d.strftime('%s') + ".%i" % (d.microsecond/1000)
            # Fix for windows strftime('%s'), and python timedelta total_seconds not exists in 2.6
            td = d - datetime(1970, 1, 1)
            total_seconds_since_epoch = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
            value = str(total_seconds_since_epoch) + ".%i" % (d.microsecond/1000)
            #
            expected_result = datetime.utcfromtimestamp(float(value))
        else:
            value = d.strftime(pattern)
            expected_result = datetime.strptime(value, pattern)
            # Deal with time formats that don't define a year explicitly
            if "%y" not in pattern.lower():
                expected_year = get_sensible_year(*expected_result.timetuple()[1:-3])
                expected_result = expected_result.replace(year = expected_year)
        log = {}
        instance.cb[cb](value, log)
        instance.assertTrue("date" in log.keys())
        instance.assertEqual(log['date'], expected_result)


class TestGenericLibrary(unittest.TestCase):
    """Unit testing for the generic libraries"""
    normalizer_path = os.environ['NORMALIZERS_PATH']
    tagTypes = get_generic_tagTypes(os.path.join(normalizer_path,
                                                 'common_tagTypes.xml'))
    cb = get_generic_callBacks(os.path.join(normalizer_path,
                                            'common_callBacks.xml'))       
        
    def test_000_availability(self):
        """Testing libraries' availability"""
        self.assertTrue( self.tagTypes != {} )
        self.assertTrue( self.cb != {} )
        
    def test_010_test_tagTypes(self):
        """Testing tagTypes' accuracy"""
        self.assertTrue(self.tagTypes['EpochTime'].compiled_regexp.match('12934824.134'))
        self.assertTrue(self.tagTypes['EpochTime'].compiled_regexp.match('12934824'))
        self.assertTrue(self.tagTypes['syslogDate'].compiled_regexp.match('Jan 23 10:23:45'))
        self.assertTrue(self.tagTypes['syslogDate'].compiled_regexp.match('Oct  6 23:05:10'))
        self.assertTrue(self.tagTypes['URL'].compiled_regexp.match('http://www.wallix.org'))
        self.assertTrue(self.tagTypes['URL'].compiled_regexp.match('https://mysecuresite.com/?myparam=myvalue&myotherparam=myothervalue'))
        self.assertTrue(self.tagTypes['Email'].compiled_regexp.match('mhu@wallix.com'))
        self.assertTrue(self.tagTypes['Email'].compiled_regexp.match('matthieu.huin@wallix.com'))
        self.assertTrue(self.tagTypes['Email'].compiled_regexp.match('John-Fitzgerald.Willis@super-duper.institution.withlotsof.subdomains.org'))
        self.assertTrue(self.tagTypes['IP'].compiled_regexp.match('192.168.1.1'))
        self.assertTrue(self.tagTypes['IP'].compiled_regexp.match('255.255.255.0'))
        # shouldn't match ...
        self.assertTrue(self.tagTypes['IP'].compiled_regexp.match('999.888.777.666'))
        self.assertTrue(self.tagTypes['MACAddress'].compiled_regexp.match('0e:88:6a:4b:00:ff'))
        self.assertTrue(self.tagTypes['ZuluTime'].compiled_regexp.match('2012-12-21'))
        self.assertTrue(self.tagTypes['ZuluTime'].compiled_regexp.match('2012-12-21T12:34:56.99'))

    # I wish there was a way to create these tests on the fly ...
    def test_020_test_time_callback(self):
        """Testing callback MM/dd/YYYY hh:mm:ss"""
        generic_time_callback_test(self, "MM/dd/YYYY hh:mm:ss")

    def test_030_test_time_callback(self):
        """Testing callback dd/MMM/YYYY:hh:mm:ss"""
        generic_time_callback_test(self, "dd/MMM/YYYY:hh:mm:ss")
        
    def test_040_test_time_callback(self):
        """Testing callback MMM dd hh:mm:ss"""
        generic_time_callback_test(self, "MMM dd hh:mm:ss")

    def test_050_test_time_callback(self):
        """Testing callback DDD MMM dd hh:mm:ss YYYY"""
        generic_time_callback_test(self, "DDD MMM dd hh:mm:ss YYYY")
        
    def test_060_test_time_callback(self):
        """Testing callback YYYY-MM-DD hh:mm:ss"""
        generic_time_callback_test(self, "YYYY-MM-DD hh:mm:ss")
        
    def test_070_test_time_callback(self):
        """Testing callback MM/DD/YY, hh:mm:ss"""
        generic_time_callback_test(self, "MM/DD/YY, hh:mm:ss")

    def test_070_test_time_callback(self):
        """Testing callback YYMMDD hh:mm:ss"""
        generic_time_callback_test(self, "YYMMDD hh:mm:ss")

    def test_080_test_time_callback(self):
        """Testing callback ISO8601"""
        generic_time_callback_test(self, "ISO8601")

    def test_090_test_time_callback(self):
        """Testing callback EPOCH"""
        generic_time_callback_test(self, "EPOCH")

    def test_100_test_time_callback(self):
        """Testing callback dd-MMM-YYYY hh:mm:ss"""
        generic_time_callback_test(self, "dd-MMM-YYYY hh:mm:ss")

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_extras
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

import logsparser.extras as extras
import unittest

class TestExtras(unittest.TestCase):
    """Unit tests for the extras libraries."""
    
    def test_00_domains(self):
        """Tests domain extraction from various addresses."""
        # feel free to complete !
        self.assertEquals(extras.get_domain("10.10.4.7"), "10.10.4.7")
        self.assertEquals(extras.get_domain("www.google.com"), "google.com")
        self.assertEquals(extras.get_domain("lucan.cs.purdue.edu"), "purdue.edu")
        
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_lognormalizer
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

import os
import unittest
import tempfile
import shutil
from logsparser.lognormalizer import LogNormalizer
from lxml.etree import parse, fromstring as XMLfromstring

class Test(unittest.TestCase):
    """Unit tests for logsparser.lognormalizer"""
    normalizer_path = os.environ['NORMALIZERS_PATH']

    def test_000_invalid_paths(self):
        """Verify that we cannot instanciate LogNormalizer on invalid paths"""
        def bleh(paths):
            n = LogNormalizer(paths)
            return n
        self.assertRaises(ValueError, bleh, [self.normalizer_path, "/path/to/nowhere"])
        self.assertRaises(ValueError, bleh, ["/path/to/nowhere",])
        self.assertRaises(StandardError, bleh, ["/usr/bin/",])
    
    def test_001_all_normalizers_activated(self):
        """ Verify that we have all normalizer
        activated when we instanciate LogNormalizer with
        an activate dict empty.
        """
        ln = LogNormalizer(self.normalizer_path)
        self.assertTrue(len(ln))
        self.assertEqual(len([an[0] for an in ln.get_active_normalizers() if an[1]]), len(ln))
        self.assertEqual(len(ln._cache), len(ln))

    def test_002_deactivate_normalizer(self):
        """ Verify that normalizer deactivation is working.
        """
        ln = LogNormalizer(self.normalizer_path)
        active_n = ln.get_active_normalizers()
        to_deactivate = active_n.keys()[:2]
        for to_d in to_deactivate:
            del active_n[to_d]
        ln.set_active_normalizers(active_n)
        ln.reload()
        self.assertEqual(len([an[0] for an in ln.get_active_normalizers().items() if an[1]]), len(ln)-2)
        self.assertEqual(len(ln._cache), len(ln)-2)

    def test_003_activate_normalizer(self):
        """ Verify that normalizer activation is working.
        """
        ln = LogNormalizer(self.normalizer_path)
        active_n = ln.get_active_normalizers()
        to_deactivate = active_n.keys()[0]
        to_activate = to_deactivate
        del active_n[to_deactivate]
        ln.set_active_normalizers(active_n)
        ln.reload()
        # now deactivation should be done so reactivate
        active_n[to_activate] = True
        ln.set_active_normalizers(active_n)
        ln.reload()
        self.assertEqual(len([an[0] for an in ln.get_active_normalizers() if an[1]]), len(ln))
        self.assertEqual(len(ln._cache), len(ln))

    def test_004_normalizer_uuid(self):
        """ Verify that we get at least uuid tag
        """
        testlog = {'raw': 'a minimal log line'}
        ln = LogNormalizer(self.normalizer_path)
        ln.lognormalize(testlog)
        self.assertTrue('uuid' in testlog.keys())

    def test_005_normalizer_test_a_syslog_log(self):
        """ Verify that lognormalizer extracts
        syslog header as tags
        """
        testlog = {'raw': 'Jul 18 08:55:35 naruto app[3245]: body message'}
        ln = LogNormalizer(self.normalizer_path)
        ln.lognormalize(testlog)
        self.assertTrue('uuid' in testlog.keys())
        self.assertTrue('date' in testlog.keys())
        self.assertEqual(testlog['body'], 'body message')
        self.assertEqual(testlog['program'], 'app')
        self.assertEqual(testlog['pid'], '3245')

    def test_006_normalizer_test_a_syslog_log_with_syslog_deactivate(self):
        """ Verify that lognormalizer does not extract
        syslog header as tags when syslog normalizer is deactivated.
        """
        testlog = {'raw': 'Jul 18 08:55:35 naruto app[3245]: body message'}
        ln = LogNormalizer(self.normalizer_path)
        active_n = ln.get_active_normalizers()
        to_deactivate = [n for n in active_n.keys() if n.find('syslog') >= 0]
        for n in to_deactivate:
            del active_n[n]
        ln.set_active_normalizers(active_n)
        ln.reload()
        ln.lognormalize(testlog)
        self.assertTrue('uuid' in testlog.keys())
        self.assertFalse('date' in testlog.keys())
        self.assertFalse('program' in testlog.keys())

    def test_007_normalizer_getsource(self):
        """ Verify we can retreive XML source
        of a normalizer.
        """
        ln = LogNormalizer(self.normalizer_path)
        source = ln.get_normalizer_source('syslog-1.0')
        self.assertEquals(XMLfromstring(source).getroottree().getroot().get('name'), 'syslog')

    def test_008_normalizer_multiple_paths(self):
        """ Verify we can can deal with multiple normalizer paths.
        """
        fdir = tempfile.mkdtemp()
        sdir = tempfile.mkdtemp()
        for f in os.listdir(self.normalizer_path):
            path_f = os.path.join(self.normalizer_path, f)
            if os.path.isfile(path_f):
                shutil.copyfile(path_f, os.path.join(fdir, f))
        shutil.move(os.path.join(fdir, 'postfix.xml'), 
                    os.path.join(sdir, 'postfix.xml'))
        ln = LogNormalizer([fdir, sdir])
        source = ln.get_normalizer_source('postfix-0.99')
        self.assertEquals(XMLfromstring(source).getroottree().getroot().get('name'), 'postfix')
        self.assertTrue(ln.get_normalizer_path('postfix-0.99').__contains__(os.path.basename(sdir)))
        self.assertTrue(ln.get_normalizer_path('syslog-1.0').__contains__(os.path.basename(fdir)))
        xml_src = ln.get_normalizer_source('syslog-1.0')
        os.unlink(os.path.join(fdir, 'syslog.xml'))
        ln.reload()
        self.assertRaises(ValueError, ln.get_normalizer_path, 'syslog-1.0')
        ln.update_normalizer(xml_src, dir_path = sdir)
        self.assertTrue(ln.get_normalizer_path('syslog-1.0').__contains__(os.path.basename(sdir)))
        shutil.rmtree(fdir)
        shutil.rmtree(sdir)

    def test_009_normalizer_multiple_version(self):
        """ Verify we can can deal with a normalizer with more than one version.
        """
        fdir = tempfile.mkdtemp()
        shutil.copyfile(os.path.join(self.normalizer_path, 'postfix.xml'),
                        os.path.join(fdir, 'postfix.xml'))
        # Change normalizer version in fdir path
        xml = parse(os.path.join(fdir, 'postfix.xml'))
        xmln = xml.getroot()
        xmln.set('version', '1.0')
        xml.write(os.path.join(fdir, 'postfix.xml'))
        ln = LogNormalizer([self.normalizer_path, fdir])
        self.assertEquals(XMLfromstring(ln.get_normalizer_source('postfix-0.99')).getroottree().getroot().get('version'), '0.99')
        self.assertEquals(XMLfromstring(ln.get_normalizer_source('postfix-1.0')).getroottree().getroot().get('version'), '1.0')
        shutil.rmtree(fdir)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_log_samples
# -*- python -*-
# -*- coding: utf-8 -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""Testing that normalization work as excepted

Here you can add samples logs to test existing or new normalizers.

In addition to examples validation defined in each normalizer xml definition
you should add validation tests here.
In this test all normalizer definitions are loaded and therefore
it is useful to detect normalization conflicts.

"""
import os
import unittest
from datetime import datetime, timedelta
import pytz

from logsparser import lognormalizer

normalizer_path = os.environ['NORMALIZERS_PATH']
ln = lognormalizer.LogNormalizer(normalizer_path)

def _get_timeoffset(timezone, localtz):
        n = datetime.now()
        return localtz.localize(n) - timezone.localize(n)

class Test(unittest.TestCase):

    def aS(self, log, subset, notexpected = (), tzinfo = None):
        """Assert that the result of normalization of a given line log has the given subset."""
        data = {'raw' : log,
                'body' : log}
        if tzinfo:
            data['_timezone'] = tzinfo
        ln.lognormalize(data)
        for key in subset:
            self.assertEqual(data[key], subset[key])
        for key in notexpected:
            self.assertFalse(key in data.keys())

    def test_simple_syslog(self):
        """Test syslog logs"""
        now = datetime.now()
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel',
                 'date': now.replace(microsecond=0)})

        self.aS("<40>%s fbo sSMTP[8847]: Cannot open mail:25" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'Cannot open mail:25',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'fbo',
                 'program': 'sSMTP',
                 'pid': '8847',
                 'date': now.replace(microsecond=0)})
        
        self.aS("%s fbo sSMTP[8847]: Cannot open mail:25" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'Cannot open mail:25',
                 'source': 'fbo',
                 'program': 'sSMTP',
                 'pid': '8847',
                 'date': now.replace(microsecond=0)})

        now = now.replace(month=now.month%12+1, day=1)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'date': now.replace(microsecond=0, 
                                                        year= now.month == 1 and now.year or now.year - 1),
                 'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel' })
        
        # test the tolerance up to the minute : 1 ...
        now = datetime.now() + timedelta(seconds = +57)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'date': now.replace(microsecond=0),
                 'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel' })
        # ... and 2
        now = datetime.now() + timedelta(seconds = +63)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'date': now.replace(microsecond=0, year=now.year-1),
                 'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel' })

    def test_syslog_with_timezone(self):
        """Test syslog logs with a timezone info"""
        try:
            # Linux/Unix specific I guess ?
            localtz = pytz.timezone(file('/etc/timezone').read()[:-1])
        except:
            self.skipTest("Could not find local timezone, skipping test")    
        # Tokyo drift
        tokyo = pytz.timezone('Asia/Tokyo')
        offset = _get_timeoffset(tokyo,localtz)
        # first test the past
        now = datetime.now() + offset + timedelta(hours=-2)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel',
                 'date': now.replace(microsecond=0)},
                 tzinfo = 'Asia/Tokyo')
        # then fight the future
        now = datetime.now() + offset + timedelta(hours=+2)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel',
                 'date': now.replace(microsecond=0, year=now.year-1)},
                 tzinfo = 'Asia/Tokyo')
        # and finally, without the tz info ?
        now = datetime.now() + offset
        total_seconds = (offset.microseconds + (offset.seconds + offset.days * 24 * 3600) * 10**6) / 10**6
        # New in python 2.7
        #total_seconds = offset.total_seconds()
        if total_seconds > 60:
            d = now.replace(microsecond=0, year=now.year-1)
        else:
            d = now.replace(microsecond=0)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel',
                 'date': d})
        # Operation Anchorage
        anchorage = pytz.timezone('America/Anchorage')
        offset = _get_timeoffset(anchorage,localtz)
        # first test the past
        now = datetime.now() + offset + timedelta(hours=-2)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel',
                 'date': now.replace(microsecond=0)},
                 tzinfo = 'America/Anchorage')
        # then fight the future
        now = datetime.now() + offset + timedelta(hours=+2)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel',
                 'date': now.replace(microsecond=0, year=now.year-1)},
                 tzinfo = 'America/Anchorage')
        # and finally, without the tz info ?
        now = datetime.now() + offset
        total_seconds = (offset.microseconds + (offset.seconds + offset.days * 24 * 3600) * 10**6) / 10**6
        # New in python 2.7
        #total_seconds = offset.total_seconds()
        if total_seconds > 60:
            d = now.replace(microsecond=0, year=now.year-1)
        else:
            d = now.replace(microsecond=0)
        self.aS("<40>%s neo kernel: tun_wallix: Disabled Privacy Extensions" % now.strftime("%b %d %H:%M:%S"),
                {'body': 'tun_wallix: Disabled Privacy Extensions',
                 'severity': 'emerg',
                 'severity_code' : '0',
                 'facility': 'syslog',
                 'facility_code' : '5',
                 'source': 'neo',
                 'program': 'kernel',
                 'date': d})
                 
    def test_postfix(self):
        """Test postfix logs"""
        self.aS("<40>Dec 21 07:49:02 hosting03 postfix/cleanup[23416]: 2BD731B4017: message-id=<20071221073237.5244419B327@paris.office.wallix.com>",
                {'program': 'postfix',
                 'component': 'cleanup',
                 'queue_id': '2BD731B4017',
                 'pid': '23416',
                 'message_id': '20071221073237.5244419B327@paris.office.wallix.com'})

#        self.aS("<40>Dec 21 07:49:01 hosting03 postfix/anvil[32717]: statistics: max connection rate 2/60s for (smtp:64.14.54.229) at Dec 21 07:40:04",
#                {'program': 'postfix',
#                 'component': 'anvil',
#                 'pid': '32717'})
#

        self.aS("<40>Dec 21 07:49:01 hosting03 postfix/pipe[23417]: 1E83E1B4017: to=<gloubi@wallix.com>, relay=vmail, delay=0.13, delays=0.11/0/0/0.02, dsn=2.0.0, status=sent (delivered via vmail service)",
                {'program': 'postfix',
                 'component': 'pipe',
                 'queue_id': '1E83E1B4017',
                 'message_recipient': 'gloubi@wallix.com',
                 'relay': 'vmail',
                 'dest_host': 'vmail',
                 'status': 'sent'})

        self.aS("<40>Dec 21 07:49:04 hosting03 postfix/smtpd[23446]: C43971B4019: client=paris.office.wallix.com[82.238.42.70]",
                {'program': 'postfix',
                 'component': 'smtpd',
                 'queue_id': 'C43971B4019',
                 'client': 'paris.office.wallix.com[82.238.42.70]',
                 'source_host': 'paris.office.wallix.com',
                 'source_ip': '82.238.42.70'})

#        self.aS("<40>Dec 21 07:52:56 hosting03 postfix/smtpd[23485]: connect from mail.gloubi.com[65.45.12.22]",
#                {'program': 'postfix',
#                 'component': 'smtpd',
#                 'ip': '65.45.12.22'})

        self.aS("<40>Dec 21 08:42:17 hosting03 postfix/pipe[26065]: CEFFB1B4020: to=<gloubi@wallix.com@autoreply.wallix.com>, orig_to=<gloubi@wallix.com>, relay=vacation, delay=4.1, delays=4/0/0/0.08, dsn=2.0.0, status=sent (delivered via vacation service)",
                {'program': 'postfix',
                 'component': 'pipe',
                 'message_recipient': 'gloubi@wallix.com@autoreply.wallix.com',
                 'orig_to': 'gloubi@wallix.com',
                 'relay': 'vacation',
                 'dest_host': 'vacation',
                 'status': 'sent'})

    def test_squid(self):
        """Test squid logs"""
        self.aS("<40>Dec 21 07:49:02 hosting03 squid[54]: 1196341497.777    784 127.0.0.1 TCP_MISS/200 106251 GET http://fr.yahoo.com/ vbe DIRECT/217.146.186.51 text/html",
                { 'program': 'squid',
                  'date': datetime(2007, 11, 29, 13, 4, 57, 777000),
                  'elapsed': '784',
                  'source_ip': '127.0.0.1',
                  'event_id': 'TCP_MISS',
                  'status': '200',
                  'len': '106251',
                  'method': 'GET',
                  'url': 'http://fr.yahoo.com/',
                  'user': 'vbe' })
        self.aS("<40>Dec 21 07:49:02 hosting03 : 1196341497.777    784 127.0.0.1 TCP_MISS/404 106251 GET http://fr.yahoo.com/gjkgf/gfgff/ - DIRECT/217.146.186.51 text/html",
                { 'program': 'squid',
                  'date': datetime(2007, 11, 29, 13, 4, 57, 777000),
                  'elapsed': '784',
                  'source_ip': '127.0.0.1',
                  'event_id': 'TCP_MISS',
                  'status': '404',
                  'len': '106251',
                  'method': 'GET',
                  'url': 'http://fr.yahoo.com/gjkgf/gfgff/' })
        self.aS("Oct 22 01:27:16 pluto squid: 1259845087.188     10 82.238.42.70 TCP_MISS/200 13121 GET http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/VABT.swf?url_download=&width=300&height=250&vidw=300&vidh=250&startbbanner=http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_in.swf&endbanner=http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_out.swf&video_hd=http://aak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_hd.flv&video_md=http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_md.flv&video_bd=http://ak.bluestreak.comm//adv/sig/%5E16238/%5E7451318/vdo_300x250_bd.flv&url_tracer=http%3A//s0b.bluestreak.com/ix.e%3Fpx%26s%3D8008666%26a%3D7451318%26t%3D&start=2&duration1=3&duration2=4&duration3=5&durration4=6&duration5=7&end=8&hd=9&md=10&bd=11&gif=12&hover1=13&hover2=14&hover3=15&hover4=16&hover5=17&hover6=18&replay=19&sound_state=off&debug=0&playback_controls=off&tracking_objeect=tracking_object_8008666&url=javascript:bluestreak8008666_clic();&rnd=346.2680651591202 fbo DIRECT/92.123.65.129 application/x-shockwave-flash",
                {'program' : "squid",
                 'date' : datetime.utcfromtimestamp(float(1259845087.188)),
                 'elapsed' : "10",
                 'source_ip' : "82.238.42.70",
                 'event_id' : "TCP_MISS",
                 'status' : "200",
                 'len' : "13121",
                 'method' : "GET",
                 'user' : "fbo",
                 'peer_status' : "DIRECT",
                 'peer_host' : "92.123.65.129",
                 'mime_type' : "application/x-shockwave-flash",
                 'url' : "http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/VABT.swf?url_download=&width=300&height=250&vidw=300&vidh=250&startbbanner=http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_in.swf&endbanner=http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_out.swf&video_hd=http://aak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_hd.flv&video_md=http://ak.bluestreak.com//adv/sig/%5E16238/%5E7451318/vdo_300x250_md.flv&video_bd=http://ak.bluestreak.comm//adv/sig/%5E16238/%5E7451318/vdo_300x250_bd.flv&url_tracer=http%3A//s0b.bluestreak.com/ix.e%3Fpx%26s%3D8008666%26a%3D7451318%26t%3D&start=2&duration1=3&duration2=4&duration3=5&durration4=6&duration5=7&end=8&hd=9&md=10&bd=11&gif=12&hover1=13&hover2=14&hover3=15&hover4=16&hover5=17&hover6=18&replay=19&sound_state=off&debug=0&playback_controls=off&tracking_objeect=tracking_object_8008666&url=javascript:bluestreak8008666_clic();&rnd=346.2680651591202"})
        self.aS("<182>Feb 27 09:22:03 golden squid[32525]: 1330330923.254 119 10.10.5.5 TCP_MISS/302 667 GET http://c.astrocenter.fr/r.aspx?M=PRFREEV3_20120226_FR_24651456&L=http*3A*2F*2Fhoroscope.20minutes.fr*2F20Minutes*2Fimages*2FMailHeader*2Faf-0--4700-MailLogo.gif&O=685037391 - DIRECT/193.200.4.204 text/html",
                {'program' : "squid",
                 'date': datetime.utcfromtimestamp(float(1330330923.254)),
                 'elapsed' : "119",
                 "source_ip" : "10.10.5.5",
                 "event_id" : "TCP_MISS",
                 "status" : "302",
                 "len" : "667",
                 "method" : "GET",
                 'url' : "http://c.astrocenter.fr/r.aspx?M=PRFREEV3_20120226_FR_24651456&L=http*3A*2F*2Fhoroscope.20minutes.fr*2F20Minutes*2Fimages*2FMailHeader*2Faf-0--4700-MailLogo.gif&O=685037391"
                 })


    def test_netfilter(self):
        """Test netfilter logs"""
        self.aS("<40>Dec 26 09:30:07 dedibox kernel: FROM_INTERNET_DENY IN=eth0 OUT= MAC=00:40:63:e7:b2:17:00:15:fa:80:47:3f:08:00 SRC=88.252.4.37 DST=88.191.34.16 LEN=48 TOS=0x00 PREC=0x00 TTL=117 ID=56818 DF PROTO=TCP SPT=1184 DPT=445 WINDOW=65535 RES=0x00 SYN URGP=0",
                { 'program': 'netfilter',
                  'inbound_int': 'eth0',
                  'dest_mac': '00:40:63:e7:b2:17',
                  'source_mac': '00:15:fa:80:47:3f',
                  'source_ip': '88.252.4.37',
                  'dest_ip': '88.191.34.16',
                  'len': '48',
                  'protocol': 'TCP',
                  'source_port': '1184',
                  'prefix': 'FROM_INTERNET_DENY',
                  'dest_port': '445' })
        self.aS("<40>Dec 26 08:45:23 dedibox kernel: TO_INTERNET_DENY IN=vif2.0 OUT=eth0 SRC=10.116.128.6 DST=82.225.197.239 LEN=121 TOS=0x00 PREC=0x00 TTL=63 ID=15592 DF PROTO=TCP SPT=993 DPT=56248 WINDOW=4006 RES=0x00 ACK PSH FIN URGP=0 ",
                { 'program': 'netfilter',
                  'inbound_int': 'vif2.0',
                  'outbound_int': 'eth0',
                  'source_ip': '10.116.128.6',
                  'dest_ip': '82.225.197.239',
                  'len': '121',
                  'protocol': 'TCP',
                  'source_port': '993',
                  'dest_port': '56248' })
        
        # One malformed log
        self.aS("<40>Dec 26 08:45:23 dedibox kernel: TO_INTERNET_DENY IN=vif2.0 OUT=eth0 DST=82.225.197.239 LEN=121 TOS=0x00 PREC=0x00 TTL=63 ID=15592 DF PROTO=TCP SPT=993 DPT=56248 WINDOW=4006 RES=0x00 ACK PSH FIN URGP=0 ",
                { 'program': 'kernel' },
                ('inbound_int', 'len'))

        self.aS("Sep 28 15:19:59 tulipe-input kernel: [1655854.311830] DROPPED: IN=eth0 OUT= MAC=32:42:cd:02:72:30:00:23:7d:c6:35:e6:08:00 SRC=10.10.4.7 DST=10.10.4.86 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=20805 DF PROTO=TCP SPT=34259 DPT=111 WINDOW=5840 RES=0x00 SYN URGP=0",
                {'program': 'netfilter',
                 'inbound_int' : "eth0",
                 'source_ip' : "10.10.4.7",
                 'dest_ip' : "10.10.4.86",
                 'len' : "60",
                 'protocol' : 'TCP',
                 'source_port' : '34259',
                 'dest_port' : '111',
                 'dest_mac' : '32:42:cd:02:72:30',
                 'source_mac' : '00:23:7d:c6:35:e6',
                 'prefix' : '[1655854.311830] DROPPED:' })


    def test_dhcpd(self):
        """Test DHCPd log normalization"""
        self.aS("<40>Dec 25 15:00:15 gnaganok dhcpd: DHCPDISCOVER from 02:1c:25:a3:32:76 via 183.213.184.122",
                { 'program': 'dhcpd',
                  'action': 'DISCOVER',
                  'source_mac': '02:1c:25:a3:32:76',
                  'via': '183.213.184.122' })
        self.aS("<40>Dec 25 15:00:15 gnaganok dhcpd: DHCPDISCOVER from 02:1c:25:a3:32:76 via vlan18.5",
                { 'program': 'dhcpd',
                  'action': 'DISCOVER',
                  'source_mac': '02:1c:25:a3:32:76',
                  'via': 'vlan18.5' })
        for log in [
            "DHCPOFFER on 183.231.184.122 to 00:13:ec:1c:06:5b via 183.213.184.122",
            "DHCPREQUEST for 183.231.184.122 from 00:13:ec:1c:06:5b via 183.213.184.122",
            "DHCPACK on 183.231.184.122 to 00:13:ec:1c:06:5b via 183.213.184.122",
            "DHCPNACK on 183.231.184.122 to 00:13:ec:1c:06:5b via 183.213.184.122",
            "DHCPDECLINE of 183.231.184.122 from 00:13:ec:1c:06:5b via 183.213.184.122 (bla)",
            "DHCPRELEASE of 183.231.184.122 from 00:13:ec:1c:06:5b via 183.213.184.122 for nonexistent lease" ]:
            self.aS("<40>Dec 25 15:00:15 gnaganok dhcpd: %s" % log,
                { 'program': 'dhcpd',
                  'source_ip': '183.231.184.122',
                  'source_mac': '00:13:ec:1c:06:5b',
                  'via': '183.213.184.122' })
        self.aS("<40>Dec 25 15:00:15 gnaganok dhcpd: DHCPINFORM from 183.231.184.122",
                { 'program': 'dhcpd',
                  'source_ip': '183.231.184.122',
                  'action': 'INFORM' })

    def test_sshd(self):
        """Test SSHd normalization"""
        self.aS("<40>Dec 26 10:32:40 naruto sshd[2274]: Failed password for bernat from 127.0.0.1 port 37234 ssh2",
                { 'program': 'sshd',
                  'action': 'fail',
                  'user': 'bernat',
                  'method': 'password',
                  'source_ip': '127.0.0.1' })
        self.aS("<40>Dec 26 10:32:40 naruto sshd[2274]: Failed password for invalid user jfdghfg from 127.0.0.1 port 37234 ssh2",
                { 'program': 'sshd',
                  'action': 'fail',
                  'user': 'jfdghfg',
                  'method': 'password',
                  'source_ip': '127.0.0.1' })
        self.aS("<40>Dec 26 10:32:40 naruto sshd[2274]: Failed none for invalid user kgjfk from 127.0.0.1 port 37233 ssh2",
                { 'program': 'sshd',
                  'action': 'fail',
                  'user': 'kgjfk',
                  'method': 'none',
                  'source_ip': '127.0.0.1' })
        self.aS("<40>Dec 26 10:32:40 naruto sshd[2274]: Accepted password for bernat from 127.0.0.1 port 37234 ssh2",
                { 'program': 'sshd',
                  'action': 'accept',
                  'user': 'bernat',
                  'method': 'password',
                  'source_ip': '127.0.0.1' })
        self.aS("<40>Dec 26 10:32:40 naruto sshd[2274]: Accepted publickey for bernat from 192.168.251.2 port 60429 ssh2",
                { 'program': 'sshd',
                  'action': 'accept',
                  'user': 'bernat',
                  'method': 'publickey',
                  'source_ip': '192.168.251.2' })
        # See http://www.ossec.net/en/attacking-loganalysis.html
        self.aS("<40>Dec 26 10:32:40 naruto sshd[2274]: Failed password for invalid user myfakeuser from 10.1.1.1 port 123 ssh2 from 192.168.50.65 port 34813 ssh2",
               { 'program': 'sshd',
                  'action': 'fail',
                  'user': 'myfakeuser from 10.1.1.1 port 123 ssh2',
                  'method': 'password',
                  'source_ip': '192.168.50.65' })
#        self.aS("Aug  1 18:30:05 knight sshd[20439]: Illegal user guest from 218.49.183.17",
#               {'program': 'sshd',
#                'source' : 'knight',
#                'user' : 'guest',
#                'source_ip': '218.49.183.17',
#                'body' : 'Illegal user guest from 218.49.183.17',
#                })

    def test_pam(self):
        """Test PAM normalization"""
        self.aS("<40>Dec 26 10:32:25 s_all@naruto sshd[2263]: pam_unix(ssh:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=localhost user=bernat",
                { 'program': 'ssh',
                  'component': 'pam_unix',
                  'type': 'auth',
                  'user': 'bernat' })
        self.aS("<40>Dec 26 10:09:01 s_all@naruto CRON[2030]: pam_unix(cron:session): session opened for user root by (uid=0)",
                { 'program': 'cron',
                  'component': 'pam_unix',
                  'type': 'session',
                  'user': 'root' })
        self.aS("<40>Dec 26 10:32:25 s_all@naruto sshd[2263]: pam_unix(ssh:auth): check pass; user unknown",
                { 'program': 'ssh',
                  'component': 'pam_unix',
                  'type': 'auth' })
        # This one should be better handled
        self.aS("<40>Dec 26 10:32:25 s_all@naruto sshd[2263]: pam_unix(ssh:auth): authentication failure; logname= uid=0 euid=0 tty=ssh ruser= rhost=localhost",
                { 'program': 'ssh',
                  'component': 'pam_unix',
                  'type': 'auth' })

    def test_lea(self):
        """Test LEA normalization"""
        self.aS("Oct 22 01:27:16 pluto lea: loc=7803|time=1199716450|action=accept|orig=fw1|i/f_dir=inbound|i/f_name=PCnet1|has_accounting=0|uuid=<47823861,00000253,7b040a0a,000007b6>|product=VPN-1 & FireWall-1|__policy_id_tag=product=VPN-1 & FireWall-1[db_tag={9F95C344-FE3F-4E3E-ACD8-60B5194BAAB4};mgmt=fw1;date=1199701916;policy_name=Standard]|src=naruto|s_port=36973|dst=fw1|service=941|proto=tcp|rule=1",
                {'program' : 'lea',
                 'id' : "7803",
                 'action' : "accept",
                 'source_host' : "naruto",
                 'source_port' : "36973",
                 'dest_host' : "fw1",
                 'dest_port' : "941",
                 'protocol' : "tcp",
                 'product' : "VPN-1 & FireWall-1",
                 'inbound_int' : "PCnet1"})

    def test_apache(self):
        """Test Apache normalization"""
        # Test Common Log Format (CLF) "%h %l %u %t \"%r\" %>s %O"
        self.aS("""127.0.0.1 - - [20/Jul/2009:00:29:39 +0300] "GET /index/helper/test HTTP/1.1" 200 889""",
                {'program' : "apache",
                 'source_ip' : "127.0.0.1",
                 'request' : 'GET /index/helper/test HTTP/1.1',
                 'len' : "889",
                 'date' : datetime(2009, 7, 20, 0, 29, 39), 
                 'body' : '127.0.0.1 - - [20/Jul/2009:00:29:39 +0300] "GET /index/helper/test HTTP/1.1" 200 889'})

        # Test "combined" log format  "%h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\""
        self.aS('10.10.4.4 - - [04/Dec/2009:16:23:13 +0100] "GET /tulipe.core.persistent.persistent-module.html HTTP/1.1" 200 2937 "http://10.10.4.86/toc.html" "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.3) Gecko/20090910 Ubuntu/9.04 (jaunty) Shiretoko/3.5.3"',
                {'program' : "apache",
                 'source_ip' : "10.10.4.4",
                 'source_logname' : "-",
                 'user' : "-",
                 'date' : datetime(2009, 12, 4, 16, 23, 13),
                 'request' : 'GET /tulipe.core.persistent.persistent-module.html HTTP/1.1',
                 'status' : "200",
                 'len' : "2937",
                 'request_header_referer_contents' : "http://10.10.4.86/toc.html",
                 'useragent' : "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.3) Gecko/20090910 Ubuntu/9.04 (jaunty) Shiretoko/3.5.3",
                 'body' : '10.10.4.4 - - [04/Dec/2009:16:23:13 +0100] "GET /tulipe.core.persistent.persistent-module.html HTTP/1.1" 200 2937 "http://10.10.4.86/toc.html" "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.1.3) Gecko/20090910 Ubuntu/9.04 (jaunty) Shiretoko/3.5.3"'})

        # Test "vhost_combined" log format "%v:%p %h %l %u %t \"%r\" %>s %O \"%{Referer}i\" \"%{User-Agent}i\""
        #TODO: Update apache normalizer to handle this format.


    def test_bind9(self):
        """Test Bind9 normalization"""
        self.aS("Oct 22 01:27:16 pluto named: client 192.168.198.130#4532: bad zone transfer request: 'www.abc.com/IN': non-authoritative zone (NOTAUTH)",
                {'event_id' : "zone_transfer_bad",
                 'zone' : "www.abc.com",
                 'source_ip' : '192.168.198.130',
                 'class' : 'IN',
                 'program' : 'named'})
        self.aS("Oct 22 01:27:16 pluto named: general: notice: client 10.10.4.4#39583: query: tpf.qa.ifr.lan IN SOA +",
                {'event_id' : "client_query",
                 'domain' : "tpf.qa.ifr.lan",
                 'category' : "general",
                 'severity' : "notice",
                 'class' : "IN",
                 'source_ip' : "10.10.4.4",
                 'program' : 'named'})
        self.aS("Oct 22 01:27:16 pluto named: createfetch: 126.92.194.77.zen.spamhaus.org A",
                {'event_id' : "fetch_request",
                 'domain' : "126.92.194.77.zen.spamhaus.org",
                 'program' : 'named'})

    def test_symantec8(self):
        """Test Symantec version 8 normalization"""
        self.aS("""200A13080122,23,2,8,TRAVEL00,SYSTEM,,,,,,,16777216,"Symantec AntiVirus Realtime Protection Loaded.",0,,0,,,,,0,,,,,,,,,,SAMPLE_COMPUTER,,,,Parent,GROUP,,8.0.93330""",
                {"program" : "symantec",
                 "date" : datetime(2002, 11, 19, 8, 1, 34),
                 "category" : "Summary",
                 "local_host" : "TRAVEL00",
                 "domain_name" : "GROUP",
                 "event_logger_type" : "System",
                 "event_id" : "GL_EVENT_RTS_LOAD",
                 "eventblock_action" : "EB_LOG",
                 "group_id" : "0",
                 "operation_flags" : "0",
                 "parent" : "SAMPLE_COMPUTER",
                 "scan_id" : "0",
                 "server_group" : "Parent",
                 "user" : "SYSTEM",
                 "version" : "8.0.93330"})

    # Need to find real symantec version 9 log lines
    def test_symantec9(self):
        """Test Symantec version 9 normalization"""
        self.aS("""200A13080122,23,2,8,TRAVEL00,SYSTEM,,,,,,,16777216,"Symantec AntiVirus Realtime Protection Loaded.",0,,0,,,,,0,,,,,,,,,,SAMPLE_COMPUTER,,,,Parent,GROUP,,9.0.93330,,,,,,,,,,,,,,,,,,,,""",
                {"program" : "symantec",
                 "date" : datetime(2002, 11, 19, 8, 1, 34),
                 "category" : "Summary",
                 "local_host" : "TRAVEL00",
                 "domain_name" : "GROUP",
                 "event_logger_type" : "System",
                 "event_id" : "GL_EVENT_RTS_LOAD",
                 "eventblock_action" : "EB_LOG",
                 "group_id" : "0",
                 "operation_flags" : "0",
                 "parent" : "SAMPLE_COMPUTER",
                 "scan_id" : "0",
                 "server_group" : "Parent",
                 "user" : "SYSTEM",
                 "version" : "9.0.93330"})
    
    def test_arkoonFAST360(self):
        """Test Arkoon FAST360 normalization"""
        self.aS('AKLOG-id=firewall time="2004-02-25 17:38:57" fw=myArkoon aktype=IP gmtime=1077727137 ip_log_type=ENDCONN src=10.10.192.61 dst=10.10.192.255 proto="137/udp" protocol=17 port_src=137 port_dest=137 intf_in=eth0 intf_out= pkt_len=78 nat=NO snat_addr=0 snat_port=0 dnat_addr=0 dnat_port=0 user="userName" pri=3 rule="myRule" action=DENY reason="Blocked by filter" description="dst addr received from Internet is private"',
                {"program" : "arkoon",
                 "date" : datetime(2004, 02, 25, 16, 38, 57),
                 "event_id" : "IP",
                 "priority" : "3",
                 "local_host" : "myArkoon",
                 "user" : "userName",
                 "protocol": "udp",
                 "dest_ip" : "10.10.192.255",
                 "source_ip" : "10.10.192.61",
                 "reason" : "Blocked by filter",
                 "ip_log_type" : "ENDCONN",
                 "body" : 'id=firewall time="2004-02-25 17:38:57" fw=myArkoon aktype=IP gmtime=1077727137 ip_log_type=ENDCONN src=10.10.192.61 dst=10.10.192.255 proto="137/udp" protocol=17 port_src=137 port_dest=137 intf_in=eth0 intf_out= pkt_len=78 nat=NO snat_addr=0 snat_port=0 dnat_addr=0 dnat_port=0 user="userName" pri=3 rule="myRule" action=DENY reason="Blocked by filter" description="dst addr received from Internet is private"'})

        # Assuming this kind of log with syslog like header is typically sent over the wire.
        self.aS('<134>IP-Logs: AKLOG - id=firewall time="2010-10-04 10:38:37" gmtime=1286181517 fw=doberman.jurassic.ta aktype=IP ip_log_type=NEWCONN src=172.10.10.107 dst=204.13.8.181 proto="http" protocol=6 port_src=2619 port_dest=80 intf_in=eth7 intf_out=eth2 pkt_len=48 nat=HIDE snat_addr=10.10.10.199 snat_port=16176 dnat_addr=0 dnat_port=0 tcp_seq=1113958286 tcp_ack=0 tcp_flags="SYN" user="" vpn-src="" pri=6 rule="surf_normal" action=ACCEPT',
                {'program': 'arkoon',
                 'event_id': 'IP',
                 'rule': 'surf_normal',
                 'ip_log_type': 'NEWCONN'})
        
        # This one must not match the arkoonFAST360 parser
        # Assuming this king of log does not exist
        self.aS('<40>Dec 21 08:42:17 hosting arkoon: <134>IP-Logs: AKLOG - id=firewall time="2010-10-04 10:38:37" gmtime=1286181517 fw=doberman.jurassic.ta aktype=IP ip_log_type=NEWCONN src=172.10.10.107 dst=204.13.8.181 proto="http" protocol=6 port_src=2619 port_dest=80 intf_in=eth7 intf_out=eth2 pkt_len=48 nat=HIDE snat_addr=10.10.10.199 snat_port=16176 dnat_addr=0 dnat_port=0 tcp_seq=1113958286 tcp_ack=0 tcp_flags="SYN" user="" vpn-src="" pri=6 rule="surf_normal" action=ACCEPT',
                {'program': 'arkoon'}, # program is set by syslog parser
                ('event_id', 'rule', 'ip_log_type'))
    
    def test_MSExchange2007MTL(self):
        """Test Exchange 2007 message tracking log normalization"""
        self.aS("""2010-04-19T12:29:07.390Z,10.10.14.73,WIN2K3DC,,WIN2K3DC,"MDB:ada3d2c3-6f32-45db-b1ee-a68dbcc86664, Mailbox:68cf09c1-1344-4639-b013-3c6f8a588504, Event:1440, MessageClass:IPM.Note, CreationTime:2010-04-19T12:28:51.312Z, ClientType:User",,STOREDRIVER,SUBMIT,,<C6539E897AEDFA469FE34D029FB708D43495@win2k3dc.qa.ifr.lan>,,,,,,,Coucou !,user7@qa.ifr.lan,,""",
                {'mdb': 'ada3d2c3-6f32-45db-b1ee-a68dbcc86664',
                 'source_host': 'WIN2K3DC',
                 'source_ip': '10.10.14.73',
                 'client_type': 'User',
                 'creation_time': 'Mon Apr 19 12:28:51 2010',
                 'date': datetime(2010, 4, 19, 12, 29, 7, 390000),
                 'event': '1440',
                 'event_id': 'SUBMIT',
                 'exchange_source': 'STOREDRIVER',
                 'mailbox': '68cf09c1-1344-4639-b013-3c6f8a588504',
                 'message_class': 'IPM.Note',
                 'message_id': 'C6539E897AEDFA469FE34D029FB708D43495@win2k3dc.qa.ifr.lan',
                 'message_subject': 'Coucou !',
                 'program': 'MS Exchange 2007 Message Tracking',
                 'dest_host': 'WIN2K3DC'})

    def test_S3(self):
        """Test Amazon S3 bucket log normalization"""
        self.aS("""DEADBEEF testbucket [19/Jul/2011:13:17:11 +0000] 10.194.22.16 FACEDEAD CAFEDECA REST.GET.ACL - "GET /?acl HTTP/1.1" 200 - 951 - 397 - "-" "Jakarta Commons-HttpClient/3.0" -""",
                {'source_ip': '10.194.22.16',
                 'http_method': 'GET',
                 'protocol': 'HTTP/1.1',
                 'status': '200',
                 'user': 'DEADBEEF',
                 'method': 'REST.GET.ACL',
                 'program': 's3'})

    def test_Snare(self):
        """Test Snare for Windows log normalization"""
	self.aS(unicode("""<13>Aug 31 15:46:47 a-zA-Z0-9_ MSWinEventLog	1	System	287	ven. août 26 16:45:45	201	4	Virtual Disk Service	Constantin	N/A	Information	a-zA-Z0-9_	None	Le service s’est arrêté.	119 """, 'utf8'),
                {
                 'criticality': '1',
                 'eventlog_source': 'System',
                 'snare_event_counter': '287',
                 'eventlog_id': '4',
                 'eventlog_name': 'Virtual Disk Service',
                 'user': 'Constantin',
                 'sid_used': 'N/A',
                 'eventlog_type': 'Information',
                 'source_host': 'a-zA-Z0-9_',
                 'eventlog_category': 'None',
                 'program' : 'EventLog',
                 'md5_checksum' : '119',
                 'eventlog_description': unicode('Le service s’est arrêté.', 'utf8')})

	self.aS(unicode("""<13>Aug 31 15:46:47 a-zA-Z0-9_ MSWinEventLog	0	Security	284	ven. août 26 16:42:01	201	4689	Microsoft-Windows-Security-Auditing	A-ZA-Z0-9_\\clo	N/A	Success Audit	a-zA-Z0-9_	Fin du processus	Un processus est terminé. Sujet : ID de sécurité : S-1-5-21-2423214773-420032381-3839276281-1000 Nom du compte : clo Domaine du compte : A-ZA-Z0-9_ ID d’ouverture de session : 0x21211 Informations sur le processus : ID du processus : 0xb4c Nom du processus : C:\\Windows\\System32\\taskeng.exe État de fin : 0x0	138 """, 'utf8'),
                { 'criticality': '0',
                 'eventlog_source': 'Security',
                 'snare_event_counter': '284',
                 'eventlog_id': '4689',
                 'eventlog_name': 'Microsoft-Windows-Security-Auditing',
                 'user': 'clo',
                 'sid_used': 'N/A',
                 'eventlog_type': 'Success Audit',
                 'source_host': 'a-zA-Z0-9_',
                 'eventlog_category': 'Fin du processus',
                 'program' : "EventLog",
                 'md5_checksum' : '138',
                 'eventlog_description': unicode('Un processus est terminé. Sujet : ID de sécurité : S-1-5-21-2423214773-420032381-3839276281-1000 Nom du compte : clo Domaine du compte : A-ZA-Z0-9_ ID d’ouverture de session : 0x21211 Informations sur le processus : ID du processus : 0xb4c Nom du processus : C:\\Windows\\System32\\taskeng.exe État de fin : 0x0', 'utf8')})

    def test_vmwareESX4_ESXi4(self):
	"""Test VMware ESX 4.x and VMware ESXi 4.x log normalization"""
	self.aS("""[2011-09-05 16:06:30.016 F4CD1B90 verbose 'Locale' opID=996867CC-000002A6] Default resource used for 'host.SystemIdentificationInfo.IdentifierType.ServiceTag.summary' expected in module 'enum'.""",
		{'date': datetime(2011, 9, 5, 16, 6, 30),
	 	 'numeric': 'F4CD1B90',
	 	 'level': 'verbose',
	 	 'alpha': 'Locale',
	 	 'body': 'Default resource used for \'host.SystemIdentificationInfo.IdentifierType.ServiceTag.summary\' expected in module \'enum\'.'})

	self.aS("""sysboot: Executing 'kill -TERM 314'""",
		{'body': 'Executing \'kill -TERM 314\''})

#    def test_mysql(self):
#	"""Test mysql log normalization"""
#	self.aS("""110923 11:04:58	   36 Query	show databases""",
#		{'date': datetime(2011, 9, 23, 11, 4, 58),
#		 'id': '36',
#	 	 'type': 'Query',
#	 	 'event': 'show databases'})
#	self.aS("""110923 10:09:11 [Note] Plugin 'FEDERATED' is disabled.""",
#		{'date': datetime(2011, 9, 23, 10, 9, 11),
#	 	 'component': 'Note',
#	 	 'event': 'Plugin \'FEDERATED\' is disabled.'})

    def test_IIS(self):
	"""Test IIS log normalization"""
	self.aS("""172.16.255.255, anonymous, 03/20/01, 23:58:11, MSFTPSVC, SALES1, 172.16.255.255, 60, 275, 0, 0, 0, PASS, /Intro.htm, -,""",
		{'source_ip': '172.16.255.255',
		 'user': 'anonymous',
		 'date': datetime(2001, 3, 20, 23, 58, 11),
		 'service': 'MSFTPSVC',
		 'dest_host': 'SALES1',
		 'dest_ip': '172.16.255.255',
		 'time_taken': 0.06,
		 'sent_bytes_number': '275',
		 'returned_bytes_number': '0',
		 'status': '0',
		 'windows_status_code': '0',
		 'method': 'PASS',
		 'url_path': '/Intro.htm',
		 'script_parameters': '-'})

	self.aS("""2011-09-26 13:57:48 W3SVC1 127.0.0.1 GET /tapage.asp - 80 - 127.0.0.1 Mozilla/4.0+(compatible;MSIE+6.0;+windows+NT5.2;+SV1;+.NET+CLR+1.1.4322) 404 0 2""",
		{'date': datetime(2011, 9, 26, 13, 57, 48),
		'service': 'W3SVC1',
		'dest_ip': '127.0.0.1',
		'method': 'GET',
		'url_path': '/tapage.asp',
		'query': '-',
		'port': '80',
		'user': '-',
		'source_ip': '127.0.0.1',
		'useragent': 'Mozilla/4.0+(compatible;MSIE+6.0;+windows+NT5.2;+SV1;+.NET+CLR+1.1.4322)',
		'status': '404',
		'substatus': '0',
		'win_status': '2'})

    def test_fail2ban(self):
        """Test fail2ban ssh banishment logs"""
        self.aS("""2011-09-25 05:09:02,371 fail2ban.filter : INFO   Log rotation detected for /var/log/auth.log""",
                {'program' : 'fail2ban',
                 'component' : 'filter',
                 'body' : "Log rotation detected for /var/log/auth.log",
                 'date' : datetime(2011,9,25,5,9,2).replace(microsecond = 371000)})
        self.aS("""2011-09-25 21:59:24,304 fail2ban.actions: WARNING [ssh] Ban 219.117.199.6""",
                {'program' : 'fail2ban',
                 'component' : 'actions',
                 'action' : "Ban",
                 'protocol' : "ssh",
                 'source_ip' : "219.117.199.6",
                 'date' : datetime(2011,9,25,21,59,24).replace(microsecond = 304000)})
                 
    def test_bitdefender(self):
        """Test bitdefender spam.log (Mail Server for UNIX version)"""
        self.aS('10/20/2011 07:24:26 BDMAILD SPAM: sender: marcelo@nitex.com.br, recipients: re@corp.com, sender IP: 127.0.0.1, subject: "Lago para pesca, piscina, charrete, Hotel Fazenda", score: 1000, stamp: " v1, build 2.10.1.12405, blacklisted, total: 1000(750)", agent: Smtp Proxy 3.1.3, action: drop (move-to-quarantine;drop), header recipients: ( "cafe almoço e janta incluso" ), headers: ( "Received: from localhost [127.0.0.1] by BitDefender SMTP Proxy on localhost [127.0.0.1] for localhost [127.0.0.1]; Thu, 20 Oct 2011 07:24:26 +0200 (CEST)" "Received: from paris.office.corp.com (go.corp.lan [10.10.1.254]) by as-bd-64.ifr.lan (Postfix) with ESMTP id 4D23D1C7    for <regis.wira@corp.com>; Thu, 20 Oct 2011 07:24:26 +0200 (CEST)" "Received: from rj50ssp.nitex.com.br (rj154ssp.nitex.com.br [177.47.99.154])    by paris.office.corp.com (Postfix) with ESMTP id 28C0D6A4891    for <re@corp.com>; Thu, 20 Oct 2011 07:17:59 +0200 (CEST)" "Received: from rj154ssp.nitex.com.br (ced-sp.tuavitoria.com.br [177.47.99.13])    by rj50ssp.nitex.com.br (Postfix) with ESMTP id 9B867132C9E;    Wed, 19 Oct 2011 22:29:20 -0200 (BRST)" ), group: "Default"',
                {'message_sender' : 'marcelo@nitex.com.br',
                 'program' : 'bitdefender',
                 'action' : 'drop',
                 'message_recipients' : 're@corp.com',
                 'date' : datetime(2011,10,20,07,24,26),
                 'reason' : 'blacklisted'})

        self.aS('10/24/2011 04:31:39 BDSCAND ERROR: failed to initialize the AV core',
                {'program' : 'bitdefender',
                 'body' : 'failed to initialize the AV core',
                 'date' : datetime(2011,10,24,04,31,39)})

    def test_simple_wabauth(self):
        """Test syslog logs"""
        #WAB 3.0
        self.aS("Dec 20 17:20:22 wab2 WAB(CORE)[18190]: type='session closed' username='admin' secondary='root@debian32' client_ip='10.10.4.25' src_protocol='SFTP_SESSION' dst_protocol='SFTP_SESSION' message=''",
                { 'account': 'root',
                  'client_ip': '10.10.4.25',
                  'date': datetime(2012, 12, 20, 17, 20, 22),
                  'dest_proto': 'SFTP_SESSION',
                  'message': '',
                  'pid': '18190',
				  'uid' : '18190',
                  'program': 'WAB(CORE)',
                  'resource': 'debian32',
                  'source': 'wab2',
                  'source_proto': 'SFTP_SESSION',
                  'type': 'session closed',
                  'username': 'admin'})

        self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='primary_authentication' timestamp='2011-12-20 17:19:35.621952' username='admin' client_ip='10.10.4.25' diagnostic='SUCCESS'",
                {'client_ip': '10.10.4.25',
                 'date': datetime(2012, 12, 20, 17, 19, 35),
                 'diagnostic': 'SUCCESS',
                 'pid': '18190',
                 'program': 'WAB(CORE)',
                 'source': 'wab2',
                 'type': 'primary_authentication',
                 'username': 'admin',
                 'result' : 'True'})
	
	self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='primary_authentication' timestamp='2011-12-20 17:19:35.621952' username='admin' client_ip='10.10.4.25' diagnostic='FAIL'",
                {'client_ip': '10.10.4.25',
                 'date': datetime(2012, 12, 20, 17, 19, 35),
                 'diagnostic': 'FAIL',
                 'pid': '18190',
                 'program': 'WAB(CORE)',
                 'source': 'wab2',
                 'type': 'primary_authentication',
                 'username': 'admin',
                 'result' : 'False'})

        self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='session opened' username='admin' secondary='root@debian32' client_ip='10.10.4.25' src_protocol='SFTP_SESSION' dst_protocol='SFTP_SESSION' message=''",
                { 'account': 'root',
                  'client_ip': '10.10.4.25',
                  'date': datetime(2012, 12, 20, 17, 19, 35),
                  'dest_proto': 'SFTP_SESSION',
                  'message': '',
                  'pid': '18190',
                  'uid': '18190',
                  'program': 'WAB(CORE)',
                  'resource': 'debian32',
                  'source': 'wab2',
                  'source_proto': 'SFTP_SESSION',
                  'type': 'session opened',
                  'username': 'admin'})
	
	#WAB 3.1
        self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='primary_authentication' timestamp='2013-01-07 11:47:30.348667' username='admin' client_ip='10.10.43.25' diagnostic=''local' -pubkey- Authentication failed' result='False'",
                {'client_ip': '10.10.43.25',
                 'date': datetime(2012, 12, 20, 17, 19, 35),
                 'diagnostic': "'local' -pubkey- Authentication failed",
                 'pid': '18190',
                 'program': 'WAB(CORE)',
                 'source': 'wab2',
                 'type': 'primary_authentication',
                 'username': 'admin',
                 'result' : 'False'})

        self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='primary_authentication' timestamp='2013-01-07 11:47:30.348667' username='admin' client_ip='10.10.43.25' diagnostic=''local' -pubkey- Authentication failed' result='True'",
                {'client_ip': '10.10.43.25',
                 'date': datetime(2012, 12, 20, 17, 19, 35),
                 'diagnostic': "'local' -pubkey- Authentication failed",
                 'pid': '18190',
                 'program': 'WAB(CORE)',
                 'source': 'wab2',
                 'type': 'primary_authentication',
                 'username': 'admin',
                 'result' : 'True'})
                 
        self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='session opened' username='admin' secondary='test@debian32' client_ip='10.10.43.25' src_protocol='SSH' dst_protocol='SSH_X11_SESSION' message='' uid='1357555658581-671692-0030488bc462'",
                { 'account': 'test',
                  'client_ip': '10.10.43.25',
                  'date': datetime(2012, 12, 20, 17, 19, 35),
                  'dest_proto': 'SSH_X11_SESSION',
                  'message': '',
                  'pid': '18190',
                  'uid': '1357555658581-671692-0030488bc462',
                  'program': 'WAB(CORE)',
                  'resource': 'debian32',
                  'source': 'wab2',
                  'source_proto': 'SSH',
                  'type': 'session opened',
                  'username': 'admin'})
	
        self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='session closed' username='admin' secondary='test@debian32' client_ip='10.10.43.25' src_protocol='SSH' dst_protocol='SSH_X11_SESSION' message='Session ended' uid='1357555658581-671692-0030488bc462'",
                { 'account': 'test',
                  'client_ip': '10.10.43.25',
                  'date': datetime(2012, 12, 20, 17, 19, 35),
                  'dest_proto': 'SSH_X11_SESSION',
                  'message': 'Session ended',
                  'pid': '18190',
                  'uid': '1357555658581-671692-0030488bc462',
                  'program': 'WAB(CORE)',
                  'resource': 'debian32',
                  'source': 'wab2',
                  'source_proto': 'SSH',
                  'type': 'session closed',
                  'username': 'admin'})
		
        self.aS("Dec 20 17:19:35 wab2 WAB(CORE)[18190]: type='session closed' username='admin' secondary='test@debian32' client_ip='10.10.43.25' src_protocol='SSH' dst_protocol='SSH_X11_SESSION' message='Killed by admin' uid='1357555658581-671692-0030488bc462'",
                { 'account': 'test',
                  'client_ip': '10.10.43.25',
                  'date': datetime(2012, 12, 20, 17, 19, 35),
                  'dest_proto': 'SSH_X11_SESSION',
                  'message': 'Killed by admin',
                  'pid': '18190',
                  'uid': '1357555658581-671692-0030488bc462',
                  'program': 'WAB(CORE)',
                  'resource': 'debian32',
                  'source': 'wab2',
                  'source_proto': 'SSH',
                  'type': 'session closed',
                  'username': 'admin'})

    def test_MSExchange2003MTL(self):
        """Test Exchange 2003 message tracking log normalization"""
        self.aS("""2012-11-29\t10:42:15 GMT\t10.10.40.254\tmx2.wallix.com\t-\tEXCHANGE\t10.10.46.74\tmhuin@exchange.wallix.fr\t1019\t353399610.5513.1354185742534.JavaMail.root@zimbra.ifr.lan\t0\t0\t2532\t1\t2012-11-29 10:42:15 GMT\t0\tVersion: 6.0.3790.4675\t-\t-\tmatthieu.huin@wallix.com\t-""",
                {
                 'source_host': 'mx2.wallix.com',
                 'source_ip': '10.10.40.254',
                 'partner' : '-',
                 'creation_time': '2012-11-29 10:42:15',
                 'date': datetime(2012, 11, 29, 10, 42, 15),
                 'message_recipient' : 'mhuin@exchange.wallix.fr',
                 'event': 'SMTP submit message to AQ',
                 'event_id': '1019',
                 'internal_message_id': '353399610.5513.1354185742534.JavaMail.root@zimbra.ifr.lan',
                 'priority' : '0',
                 'recipient_status' : '0',
                 'len' : '2532',
                 'recipient_count' : '1',
                 'encryption': '0',
                 'service_version' : "Version: 6.0.3790.4675",
                 'linked_message_id' : '-',
                 'message_subject' : "-",
                 "message_sender" : "matthieu.huin@wallix.com",
                 'program': 'MS Exchange 2003 Message Tracking',
                 'dest_host': 'EXCHANGE',
                 'dest_ip': '10.10.46.74',})

    def test_xferlog(self):
        """Testing xferlog formatted logs"""
        self.aS("Thu Sep 2 09:52:00 2004 50 192.168.20.10 896242 /home/test/file1.tgz b _ o r suporte ftp 0 * c ",
                {'transfer_time' : '50',
                 'source_ip' : '192.168.20.10',
                 'len' : '896242',
                 'filename' : '/home/test/file1.tgz',
                 'transfer_type_code' : 'b',
                 'special_action_flag' : '_',
                 'direction_code' : 'o',
                 'access_mode_code' : 'r',
                 'completion_status_code' : 'c',
                 'authentication_method_code' : '0',
                 'transfer_type' : 'binary',
                 'special_action' : 'none',
                 'direction' : 'outgoing',
                 'access_mode' : 'real',
                 'completion_status' : 'complete',
                 'authentication_method' : 'none',
                 'user' : 'suporte',
                 'service_name' : 'ftp',
                 'authenticated_user_id' : '*',
                 'program' : 'ftpd',
                 'date' : datetime(2004,9,2,9,52),})
        self.aS("Tue Dec 27 11:24:23 2011 1 127.0.0.1 711074 /home/mhu/Documents/Brooks,_Max_-_World_War_Z.mobi b _ o r mhu ftp 0 * c",
                {'transfer_time' : '1',
                 'source_ip' : '127.0.0.1',
                 'len' : '711074',
                 'filename' : '/home/mhu/Documents/Brooks,_Max_-_World_War_Z.mobi',
                 'transfer_type_code' : 'b',
                 'special_action_flag' : '_',
                 'direction_code' : 'o',
                 'access_mode_code' : 'r',
                 'completion_status_code' : 'c',
                 'authentication_method_code' : '0',
                 'transfer_type' : 'binary',
                 'special_action' : 'none',
                 'direction' : 'outgoing',
                 'access_mode' : 'real',
                 'completion_status' : 'complete',
                 'authentication_method' : 'none',
                 'user' : 'mhu',
                 'service_name' : 'ftp',
                 'authenticated_user_id' : '*',
                 'program' : 'ftpd',
                 'date' : datetime(2011,12,27,11,24,23),}) 
 
    def test_dansguardian(self):
        """Testing dansguardian logs"""
        self.aS("2011.12.13 10:41:28 10.10.42.23 10.10.42.23 http://safebrowsing.clients.google.com/safebrowsing/downloads?client=Iceweasel&appver=3.5.16&pver=2.2&wrkey=AKEgNityGqylPYNyNETvnRjDjo4mIKcwv7f-8UCJaKERjXG6cXrikbgdA0AG6J8A6zng73h9U1GoE7P5ZPn0dDLmD_t3q1csCw== *EXCEPTION* Site interdit trouv&ecute;. POST 491 0  2 200 -  limited_access -",
                {'program' : 'dansguardian',
                 'user' : '10.10.42.23',
                 'source_ip' : '10.10.42.23',
                 'url' : 'http://safebrowsing.clients.google.com/safebrowsing/downloads?client=Iceweasel&appver=3.5.16&pver=2.2&wrkey=AKEgNityGqylPYNyNETvnRjDjo4mIKcwv7f-8UCJaKERjXG6cXrikbgdA0AG6J8A6zng73h9U1GoE7P5ZPn0dDLmD_t3q1csCw==',
                 'actions' : "*EXCEPTION*",
                 'action' : 'EXCEPTION',
                 'reason' : "Site interdit trouv&ecute;.",
                 "method" : "POST",
                 "len" : "491",
                 "naughtiness" : "0",
                 "filter_group_number" : "2",
                 "status" : "200",
                 "mime_type" : "-",
                 "filter_group_name" : "limited_access",
                 'date' : datetime(2011,12,13,10,41,28),})

    def test_deny_event(self):
        """Testing denyAll event logs"""
        self.aS("""224,2011-01-24 17:44:46.061903,2011-01-24 17:44:46.061903,,,192.168.219.10,127.0.0.1,,2,1,4,0,"Session opened (read-write), Forwarded for 192.168.219.1.",superadmin,gui,,{403ec510-27d9-11e0-bbe7-000c298895c5}Session,,,,,,,,,,,,,,,,,,,,""",
                {'alert_id': '0',
                 'alert_subtype': 'Access',
                 'alert_subtype_id': '1',
                 'alert_type': 'System',
                 'alert_type_id': '2',
                 'alert_value': 'Session opened (read-write), Forwarded for 192.168.219.1.',
                 'body': '224,2011-01-24 17:44:46.061903,2011-01-24 17:44:46.061903,,,192.168.219.10,127.0.0.1,,2,1,4,0,"Session opened (read-write), Forwarded for 192.168.219.1.",superadmin,gui,,{403ec510-27d9-11e0-bbe7-000c298895c5}Session,,,,,,,,,,,,,,,,,,,,',
                 'date': datetime(2011, 1, 24, 17, 44, 46),
                 'end_date': '2011-01-24 17:44:46.061903',
                 'event': 'User successful login',
                 'event_uid': '224',
                 'interface': 'gui',
                 'ip_device': '192.168.219.10',
                 'parameter_changed': '{403ec510-27d9-11e0-bbe7-000c298895c5}Session',
                 'raw': '224,2011-01-24 17:44:46.061903,2011-01-24 17:44:46.061903,,,192.168.219.10,127.0.0.1,,2,1,4,0,"Session opened (read-write), Forwarded for 192.168.219.1.",superadmin,gui,,{403ec510-27d9-11e0-bbe7-000c298895c5}Session,,,,,,,,,,,,,,,,,,,,',
                 'severity': 'Warn',
                 'severity_code': '4',
                 'source_ip': '127.0.0.1',
                 'user': 'superadmin'})
        self.aS("""1,2011-01-20 15:09:38.130965,2011-01-20 15:09:38.130965,,,::1,,,2,2,5,0,rWeb started.,,,,,,,,,,,,,,,,,,,,,,,,""",
               {'alert_id': '0',
                'alert_subtype': 'Device Operations',
                'alert_subtype_id': '2',
                'alert_type': 'System',
                'alert_type_id': '2',
                'alert_value': 'rWeb started.',
                'body': '1,2011-01-20 15:09:38.130965,2011-01-20 15:09:38.130965,,,::1,,,2,2,5,0,rWeb started.,,,,,,,,,,,,,,,,,,,,,,,,',
                'date': datetime(2011, 1, 20, 15, 9, 38),
                'end_date': '2011-01-20 15:09:38.130965',
                'event': 'rWeb started',
                'event_uid': '1',
                'ip_device': '::1',
                'raw': '1,2011-01-20 15:09:38.130965,2011-01-20 15:09:38.130965,,,::1,,,2,2,5,0,rWeb started.,,,,,,,,,,,,,,,,,,,,,,,,',
                'severity': 'Notice',
                'severity_code': '5'} )

    def test_cisco_asa(self):
        """Testing CISCO ASA logs"""
        self.aS("""<168>Mar 05 2010 11:06:12 ciscoasa : %ASA-6-305011: Built dynamic TCP translation from 14net:14.36.103.220/300 to 172net:172.18.254.146/55""",
               {'program': 'cisco-asa',
                'severity_code': '6',
                'event_id': '305011',
                'date': datetime(2010, 3, 5, 11, 6, 12),
                'taxonomy': 'firewall',
                'outbound_int': '172net',
                'dest_port': '55'})
        self.aS("""<168>Jul 02 2006 07:33:45 ciscoasa : %ASA-6-302013: Built outbound TCP connection 8300517 for outside:64.156.4.191/110 (64.156.4.191/110) to inside:192.168.8.12/3109 (xxx.xxx.185.142/11310)""",
               {'program': 'cisco-asa',
                'severity_code': '6',
                'event_id': '302013',
                'date': datetime(2006, 7, 2, 7, 33, 45),
                'taxonomy': 'firewall',
                'outbound_int': 'inside',
                'dest_ip': '192.168.8.12'})

    def test_openLDAP(self):
        """Testing openLDAP logs"""
        self.aS("""Jun 12 11:18:47 openLDAP slapd[870]: conn=1007 op=0 RESULT tag=97 err=53 text=unauthenticated bind (DN with no password) disallowed""",
               {'program': 'slapd',
                'source': 'openLDAP',
                'connection_id' : '1007',
                'operation_id' : '0',
                'action' : 'RESULT',
                'tag_code' : '97',
                'error_code': '53',
                'response_type' : 'Bind',
                'status' : 'Service error - unwilling to perform',
                'reason' : 'unauthenticated bind (DN with no password) disallowed',
                })
        self.aS('Jun 12 11:14:20 openLDAP slapd[870]: conn=1002 op=0 SRCH base="" scope=0 deref=0 filter="(objectClass=*)"',
               {'program': 'slapd',
                'source': 'openLDAP',
                'connection_id' : '1002',
                'operation_id' : '0',
                'action' : 'SRCH',
                'deref' : '0',
                'scope_code': '0',
                'scope' : 'base',
                'filter' : '(objectClass=*)',
                })
        self.aS('Jun 11 15:52:37 openLDAP slapd[1814]: conn=1012 fd=14 ACCEPT from IP=10.10.4.7:39450 (IP=10.10.4.250:389)',
               {'program': 'slapd',
                'source': 'openLDAP',
                'connection_id' : '1012',
                'socket_id' : '14',
                'action' : 'ACCEPT',
                'source_ip' : '10.10.4.7',
                'source_port': '39450',
                'local_ip' : '10.10.4.250',
                'local_port' : '389',
                })

    def test_eventlogW3EN(self):
        """Testing Win2003 security audit logs (english)"""
        self.aS("""<13>Nov 21 16:28:40 w2003en MSWinEventLog	0\tSecurity\t129\tWed Nov 21 16:28:40\t2012\t592\tSecurity\tSYSTEM\tUser\tSuccess Audit\tW2003EN\tDetailed Tracking\tA new process has been created:     New Process ID: 1536     Image File Name: C:\WINDOWS\system32\wpabaln.exe     Creator Process ID: 540     User Name: W2003EN$     Domain: WORKGROUP     Logon ID: (0x0,0x3E7)\t99""",
               {
                 'criticality': '0',
                 'eventlog_id': '592',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Security',
                 'source_host': 'W2003EN',
                 'eventlog_type': 'Success Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '99',
                 'eventlog_description': """A new process has been created:     New Process ID: 1536     Image File Name: C:\WINDOWS\system32\wpabaln.exe     Creator Process ID: 540     User Name: W2003EN$     Domain: WORKGROUP     Logon ID: (0x0,0x3E7)""",
                 "file_name" : "C:\WINDOWS\system32\wpabaln.exe",
                 "user" : "W2003EN$",
                 "domain" : "WORKGROUP",
                 "logon_id" : "(0x0,0x3E7)",
                 "pid" : "1536",})         

        self.aS("""<13>Nov 21 17:45:05 w2003en MSWinEventLog 1\tSecurity\t233\tWed Nov 21 17:44:59\t2012\t529\tSecurity\tSYSTEM\tUser\tFailure Audit\tW2003EN\tLogon/Logoff\tLogon Failure:     Reason: Unknown user name or bad password     User Name: Administrator     Domain: W2003EN     Logon Type: 2     Logon Process: User32       Authentication Package: Negotiate     Workstation Name: W2003EN     Caller User Name: W2003EN$     Caller Domain: WORKGROUP     Caller Logon ID: (0x0,0x3E7)     Caller Process ID: 484     Transited Services: -     Source Network Address: 127.0.0.1     Source Port: 0\t206""", 
               {'criticality': '1',
                 'eventlog_id': '529',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Security',
                 'source_host': 'W2003EN',
                 'eventlog_type': 'Failure Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '206',
                 "user" : "Administrator",
                 "domain" : "W2003EN",
                 "logon_type" : "2",
                 "method" : "Interactive",
                 "authentication_package" : 'Negotiate',
                 "dest_host" : "W2003EN",
                 "caller" : "W2003EN$",
                 "caller_domain" : "WORKGROUP",
                 "caller_logon_id" : "(0x0,0x3E7)",
                 "status" : "failure",
                 "reason" : "Unknown user name or bad password",
                 "source_ip" : "127.0.0.1",
                 "source_port" : "0",
                 'eventlog_description': """Logon Failure:     Reason: Unknown user name or bad password     User Name: Administrator     Domain: W2003EN     Logon Type: 2     Logon Process: User32       Authentication Package: Negotiate     Workstation Name: W2003EN     Caller User Name: W2003EN$     Caller Domain: WORKGROUP     Caller Logon ID: (0x0,0x3E7)     Caller Process ID: 484     Transited Services: -     Source Network Address: 127.0.0.1     Source Port: 0""", })  

        self.aS("""<13>Nov 21 17:45:25 w2003en MSWinEventLog	1\tSecurity\t237\tWed Nov 21 17:45:25\t2012\t576\tSecurity\tAdministrator\tUser\tSuccess Audit\tW2003EN\tPrivilege Use\tSpecial privileges assigned to new logon:     User Name: Administrator     Domain: W2003EN     Logon ID: (0x0,0x3A092)     Privileges: SeSecurityPrivilege   SeBackupPrivilege   SeRestorePrivilege   SeTakeOwnershipPrivilege   SeDebugPrivilege   SeSystemEnvironmentPrivilege   SeLoadDriverPrivilege   SeImpersonatePrivilege\t210""", 
               {'criticality': '1',
                 'eventlog_id': '576',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Security',
                 'source_host': 'W2003EN',
                 'eventlog_type': 'Success Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '210',
                 "user" : "Administrator",
                 "domain" : "W2003EN",
                 "logon_id" : "(0x0,0x3A092)",
                 "privileges" : "SeSecurityPrivilege   SeBackupPrivilege   SeRestorePrivilege   SeTakeOwnershipPrivilege   SeDebugPrivilege   SeSystemEnvironmentPrivilege   SeLoadDriverPrivilege   SeImpersonatePrivilege",
                 'eventlog_description': """Special privileges assigned to new logon:     User Name: Administrator     Domain: W2003EN     Logon ID: (0x0,0x3A092)     Privileges: SeSecurityPrivilege   SeBackupPrivilege   SeRestorePrivilege   SeTakeOwnershipPrivilege   SeDebugPrivilege   SeSystemEnvironmentPrivilege   SeLoadDriverPrivilege   SeImpersonatePrivilege""", })  

    def test_MSExchangeISMailboxStore2003(self):
        """Testing MSExchangeIS Mailbox Store logs for exchange 2003"""
        self.aS(u"""<13>Dec  3 18:14:15 exchange.q-ass.lan MSWinEventLog 1\tApplication\t127867\tMon Dec 03 18:14:13\t2012\t1016\tMSExchangeIS Mailbox Store\tUnknown User\tN/A\tSuccess Audit\tEXCHANGE\tOuvertures de session\tL'utilisateur Windows 2000 Q-ASS\mhu s'est connecté à la boîte aux lettres scr@exchange.wallix.fr et n'est pas le compte principal Windows 2000 de cette boîte aux lettres.      Pour plus d'informations, visitez le site http://www.microsoft.com/contentredirect.asp.\t711""",
               {
                 'criticality': '1',
                 'eventlog_id': '1016',
                 'eventlog_source': 'Application',
                 'eventlog_name': 'MSExchangeIS Mailbox Store',
                 'source_host': 'EXCHANGE',
                 'eventlog_type': 'Success Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '711',
                 'eventlog_description': u"""L'utilisateur Windows 2000 Q-ASS\mhu s'est connecté à la boîte aux lettres scr@exchange.wallix.fr et n'est pas le compte principal Windows 2000 de cette boîte aux lettres.      Pour plus d'informations, visitez le site http://www.microsoft.com/contentredirect.asp.""",
                 "user" : u"Q-ASS\\mhu",
                 "mailbox_owner" : "scr@exchange.wallix.fr",
                 })  
                 
    def test_eventlogW8EN(self):
        """Testing Win2008 security audit logs (english)"""
        self.aS(u"""<13>Nov 21 17:45:25 WIN-D7NM05T4KNM    MSWinEventLog    1\tSecurity\t399\tThu Jan 31 13:18:31\t2013\t4624\tMicrosoft-Windows-Security-Auditing\tWIN-D7NM05T4KNM\Administrator\tN/A\tSuccess Audit\tWIN-D7NM05T4KNM\tLogon\tAn account was successfully logged on. Subject: Security ID: S-1-5-18 Account Name: WIN-D7NM05T4KNM$ Account Domain: WORKGROUP Logon ID: 0x3e7 Logon Type: 2 New Logon: Security ID: S-1-5-21-2218251928-2375033965-419438225-500 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon ID: 0xd30cd Logon GUID: {00000000-0000-0000-0000-000000000000} Process Information: Process ID: 0x5e0 Process Name: C:\Windows\System32\winlogon.exe Network Information: Workstation Name: WIN-D7NM05T4KNM Source Network Address: 127.0.0.1 Source Port: 0 Detailed Authentication Information: Logon Process: User32 Authentication Package: Negotiate Transited Services: - Package Name (NTLM only): - Key Length: 0 This event is generated when a logon session is created. It is generated on the computer that was accessed. The subject fields indicate the account on the local system which requested the logon. This is most commonly a service such as the Server service, or a local process such as Winlogon.exe or Services.exe. The logon type field indicates the kind of logon that occurred. The most common types are 2 (interactive) and 3 (network). The New Logon fields indicate the account for whom the new logon was created, i.e. the account that was logged on. The network fields indicate where a remote logon request originated. Workstation name is not always available and may be left blank in some cases. The authentication information fields provide detailed information about this specific logon request. - Logon GUID is a unique identifier that can be used to correlate this event with a KDC event. - Transited services indicate which intermediate services have participated in this logon request. - Package name indicates which sub-protocol was used among the NTLM protocols. - Key length indicates the length of the generated session key. This will be 0 if no session key was requested.\t271""",
                {
                 'criticality': '1',
                 'eventlog_id': '4624',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Microsoft-Windows-Security-Auditing',
                 'source_host': 'WIN-D7NM05T4KNM',
                 'eventlog_type': 'Success Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '271',
                 'eventlog_description': """An account was successfully logged on. Subject: Security ID: S-1-5-18 Account Name: WIN-D7NM05T4KNM$ Account Domain: WORKGROUP Logon ID: 0x3e7 Logon Type: 2 New Logon: Security ID: S-1-5-21-2218251928-2375033965-419438225-500 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon ID: 0xd30cd Logon GUID: {00000000-0000-0000-0000-000000000000} Process Information: Process ID: 0x5e0 Process Name: C:\Windows\System32\winlogon.exe Network Information: Workstation Name: WIN-D7NM05T4KNM Source Network Address: 127.0.0.1 Source Port: 0 Detailed Authentication Information: Logon Process: User32 Authentication Package: Negotiate Transited Services: - Package Name (NTLM only): - Key Length: 0 This event is generated when a logon session is created. It is generated on the computer that was accessed. The subject fields indicate the account on the local system which requested the logon. This is most commonly a service such as the Server service, or a local process such as Winlogon.exe or Services.exe. The logon type field indicates the kind of logon that occurred. The most common types are 2 (interactive) and 3 (network). The New Logon fields indicate the account for whom the new logon was created, i.e. the account that was logged on. The network fields indicate where a remote logon request originated. Workstation name is not always available and may be left blank in some cases. The authentication information fields provide detailed information about this specific logon request. - Logon GUID is a unique identifier that can be used to correlate this event with a KDC event. - Transited services indicate which intermediate services have participated in this logon request. - Package name indicates which sub-protocol was used among the NTLM protocols. - Key length indicates the length of the generated session key. This will be 0 if no session key was requested.""",
                 'security_id': 'S-1-5-18',
                 'old_user': 'WIN-D7NM05T4KNM$',
                 'old_domain': 'WORKGROUP',
                 'old_logon_id': '0x3e7',
                 'logon_type':'2',
                 'method': 'Interactive',
                 'security_id': 'S-1-5-21-2218251928-2375033965-419438225-500',
                 'user': 'Administrator',
                 'domain': 'WIN-D7NM05T4KNM',
                 'logon_id': '0xd30cd',
                 'logon_guid': '{00000000-0000-0000-0000-000000000000}',
                 'pid': '0x5e0',
                 'process_name': 'C:\Windows\System32\winlogon.exe',
                 'workstation_name':'WIN-D7NM05T4KNM',
                 'source_ip': '127.0.0.1',
                 'source_port': '0',
                 'logon_process': 'User32',
                 'authentification_package': 'Negotiate',
                 'transited_services': '-',
                 'package_name': '-',
                 'key_length': '0',
                 'status' : 'success'
                 })
        
        self.aS(u"""<13>Nov 21 17:45:25 WIN-D7NM05T4KNM    MSWinEventLog    1\tSecurity\t392\tThu Jan 31 13:18:27\t2013\t4625\tMicrosoft-Windows-Security-Auditing\tWIN-D7NM05T4KNM\Administrator\tN/A\tFailure Audit\tWIN-D7NM05T4KNM\tLogon\tAn account failed to log on. Subject: Security ID: S-1-5-18 Account Name: WIN-D7NM05T4KNM$ Account Domain: WORKGROUP Logon ID: 0x3e7 Logon Type: 2 Account For Which Logon Failed: Security ID: S-1-0-0 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Failure Information: Failure Reason: Unknown user name or bad password. Status: 0xc000006d Sub Status: 0xc000006a Process Information: Caller Process ID: 0x5e0 Caller Process Name: C:\Windows\System32\winlogon.exe Network Information: Workstation Name: WIN-D7NM05T4KNM Source Network Address: 127.0.0.1 Source Port: 0 Detailed Authentication Information: Logon Process: User32 Authentication Package: Negotiate Transited Services: - Package Name (NTLM only): - Key Length: 0 This event is generated when a logon request fails. It is generated on the computer where access was attempted. The Subject fields indicate the account on the local system which requested the logon. This is most commonly a service such as the Server service, or a local process such as Winlogon.exe or Services.exe. The Logon Type field indicates the kind of logon that was requested. The most common types are 2 (interactive) and 3 (network). The Process Information fields indicate which account and process on the system requested the logon. The Network Information fields indicate where a remote logon request originated. Workstation name is not always available and may be left blank in some cases. The authentication information fields provide detailed information about this specific logon request. - Transited services indicate which intermediate services have participated in this logon request. - Package name indicates which sub-protocol was used among the NTLM protocols. - Key length indicates the length of the generated session key. This will be 0 if no session key was requested.\t268""",
                {
                 'criticality': '1',
                 'eventlog_id': '4625',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Microsoft-Windows-Security-Auditing',
                 'source_host': 'WIN-D7NM05T4KNM',
                 'eventlog_type': 'Failure Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '268',
                 'eventlog_description': """An account failed to log on. Subject: Security ID: S-1-5-18 Account Name: WIN-D7NM05T4KNM$ Account Domain: WORKGROUP Logon ID: 0x3e7 Logon Type: 2 Account For Which Logon Failed: Security ID: S-1-0-0 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Failure Information: Failure Reason: Unknown user name or bad password. Status: 0xc000006d Sub Status: 0xc000006a Process Information: Caller Process ID: 0x5e0 Caller Process Name: C:\Windows\System32\winlogon.exe Network Information: Workstation Name: WIN-D7NM05T4KNM Source Network Address: 127.0.0.1 Source Port: 0 Detailed Authentication Information: Logon Process: User32 Authentication Package: Negotiate Transited Services: - Package Name (NTLM only): - Key Length: 0 This event is generated when a logon request fails. It is generated on the computer where access was attempted. The Subject fields indicate the account on the local system which requested the logon. This is most commonly a service such as the Server service, or a local process such as Winlogon.exe or Services.exe. The Logon Type field indicates the kind of logon that was requested. The most common types are 2 (interactive) and 3 (network). The Process Information fields indicate which account and process on the system requested the logon. The Network Information fields indicate where a remote logon request originated. Workstation name is not always available and may be left blank in some cases. The authentication information fields provide detailed information about this specific logon request. - Transited services indicate which intermediate services have participated in this logon request. - Package name indicates which sub-protocol was used among the NTLM protocols. - Key length indicates the length of the generated session key. This will be 0 if no session key was requested.""",
                 'old_security_id': 'S-1-5-18',
                 'old_user': 'WIN-D7NM05T4KNM$',
                 'old_domain': 'WORKGROUP',
                 'old_logon_id': '0x3e7',
                 'logon_type': '2',
                 'method': 'Interactive',                   
                 'security_id': 'S-1-0-0',
                 'user': 'Administrator',
                 'domain': 'WIN-D7NM05T4KNM',
                 'failure_reason': 'Unknown user name or bad password.',
                 'failure_status': '0xc000006d',
                 'failure_sub_status': '0xc000006a',
                 'caller_pid': '0x5e0',
                 'caller_process_name': 'C:\Windows\System32\winlogon.exe',
                 'workstation_name': 'WIN-D7NM05T4KNM',
                 'source_ip': '127.0.0.1',
                 'source_port':'0',
                 'logon_process': 'User32',
                 'authentification_package': 'Negotiate',
                 'transited_services': '-',
                 'package_name' : '-',
                 'key_length': '0',
                 'status': 'failure'           
                 })
        
        self.aS(u"""<13>Nov 21 17:45:25 WIN-D7NM05T4KNM    MSWinEventLog    1\tSecurity\t384\tThu Jan 31 13:18:19\t2013\t4634\tMicrosoft-Windows-Security-Auditing\tWIN-D7NM05T4KNM\Administrator\tN/A\tSuccess Audit\tWIN-D7NM05T4KNM\tLogoff\tAn account was logged off. Subject: Security ID: S-1-5-21-2218251928-2375033965-419438225-500 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon ID: 0xa2a99 Logon Type: 2 This event is generated when a logon session is destroyed. It may be positively correlated with a logon event using the Logon ID value. Logon IDs are only unique between reboots on the same computer.\t260""",
                {
                 'criticality': '1',
                 'eventlog_id': '4634',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Microsoft-Windows-Security-Auditing',
                 'source_host': 'WIN-D7NM05T4KNM',
                 'eventlog_type': 'Success Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '260',
                 'eventlog_description': """An account was logged off. Subject: Security ID: S-1-5-21-2218251928-2375033965-419438225-500 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon ID: 0xa2a99 Logon Type: 2 This event is generated when a logon session is destroyed. It may be positively correlated with a logon event using the Logon ID value. Logon IDs are only unique between reboots on the same computer.""",
                 'security_id': 'S-1-5-21-2218251928-2375033965-419438225-500',
                 'user': 'Administrator',
                 'domain': 'WIN-D7NM05T4KNM',
                 'logon_id': '0xa2a99',
                 'logon_type' : '2',
                 'method': 'Interactive'                   
                 })
        
        self.aS(u"""<13>Nov 21 17:45:25 WIN-D7NM05T4KNM    MSWinEventLog    1\tSecurity\t378\tThu Jan 31 13:18:18\t2013\t4647\tMicrosoft-Windows-Security-Auditing\tWIN-D7NM05T4KNM\Administrator\tN/A\tSuccess Audit\tWIN-D7NM05T4KNM\tLogoff\tUser initiated logoff: Subject: Security ID: S-1-5-21-2218251928-2375033965-419438225-500 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon ID: 0xa2a99 This event is generated when a logoff is initiated. No further user-initiated activity can occur. This event can be interpreted as a logoff event.\t255""",
                {'criticality': '1',
                 'eventlog_id': '4647',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Microsoft-Windows-Security-Auditing',
                 'source_host': 'WIN-D7NM05T4KNM',
                 'eventlog_type': 'Success Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '255',
                 'eventlog_description':"""User initiated logoff: Subject: Security ID: S-1-5-21-2218251928-2375033965-419438225-500 Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon ID: 0xa2a99 This event is generated when a logoff is initiated. No further user-initiated activity can occur. This event can be interpreted as a logoff event.""",
                 'security_id': 'S-1-5-21-2218251928-2375033965-419438225-500',
                 'user' : 'Administrator',
                 'domain': 'WIN-D7NM05T4KNM',
                 'logon_id': '0xa2a99',
                 
                 })
        
        self.aS(u"""<13>Nov 21 17:45:25 WIN-D7NM05T4KNM    MSWinEventLog    1\tSecurity\t398\tThu Jan 31 13:18:31\t2013\t4648\tMicrosoft-Windows-Security-Auditing\tWIN-D7NM05T4KNM\Administrator\tN/A\tSuccess Audit\tWIN-D7NM05T4KNM\tLogon\tA logon was attempted using explicit credentials. Subject: Security ID: S-1-5-18 Account Name: WIN-D7NM05T4KNM$ Account Domain: WORKGROUP Logon ID: 0x3e7 Logon GUID: {00000000-0000-0000-0000-000000000000} Account Whose Credentials Were Used: Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon GUID: {00000000-0000-0000-0000-000000000000} Target Server: Target Server Name: localhost Additional Information: localhost Process Information: Process ID: 0x5e0 Process Name: C:\Windows\System32\winlogon.exe Network Information: Network Address: 127.0.0.1 Port: 0 This event is generated when a process attempts to log on an account by explicitly specifying that account’s credentials. This most commonly occurs in batch-type configurations such as scheduled tasks, or when using the RUNAS command.\t270""",
                {'criticality': '1',
                 'eventlog_id': '4648',
                 'eventlog_source': 'Security',
                 'eventlog_name': 'Microsoft-Windows-Security-Auditing',
                 'source_host': 'WIN-D7NM05T4KNM',
                 'eventlog_type': 'Success Audit',
                 'program' : 'EventLog',
                 'md5_checksum' : '270',
                 'eventlog_description': unicode("""A logon was attempted using explicit credentials. Subject: Security ID: S-1-5-18 Account Name: WIN-D7NM05T4KNM$ Account Domain: WORKGROUP Logon ID: 0x3e7 Logon GUID: {00000000-0000-0000-0000-000000000000} Account Whose Credentials Were Used: Account Name: Administrator Account Domain: WIN-D7NM05T4KNM Logon GUID: {00000000-0000-0000-0000-000000000000} Target Server: Target Server Name: localhost Additional Information: localhost Process Information: Process ID: 0x5e0 Process Name: C:\Windows\System32\winlogon.exe Network Information: Network Address: 127.0.0.1 Port: 0 This event is generated when a process attempts to log on an account by explicitly specifying that account’s credentials. This most commonly occurs in batch-type configurations such as scheduled tasks, or when using the RUNAS command.""", "utf_8"),
                 'security_id': 'S-1-5-18',
                 'user': 'WIN-D7NM05T4KNM$',
                 'domain': 'WORKGROUP',
                 'logon_id': '0x3e7',
                 'logon_guid': '{00000000-0000-0000-0000-000000000000}',
                 'credentials_account_name': 'Administrator',                  
                 'credentials_account_domain': 'WIN-D7NM05T4KNM',
                 'credentials_logon_guid': '{00000000-0000-0000-0000-000000000000}',
                 'target_server_name': 'localhost',
                 'additional_information': 'localhost',
                 'pid': '0x5e0',
                 'process_name': 'C:\Windows\System32\winlogon.exe',
                 'address': '127.0.0.1',
                 'port': '0',
                 'status': 'failure',
                 })               
        
    def test_wabObjects(self):
        """Testing WAB objects logs"""
        self.aS(u"""<14>Jul 11 11:49:21 wab2-3-1-4 wabengine: [-] Group 'foo' has just been saved by admin""",
                { 'wab_object_type': 'Group',
                  'wab_object_content': 'foo',
                  'wab_object_action': 'save',
                  'by_user': 'admin',
                 
                 })
        
                
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_normalizer
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

import os
import unittest
from datetime import datetime
from logsparser.normalizer import Normalizer, TagType, Tag, CallbackFunction, CSVPattern, get_generic_tagTypes
from lxml.etree import parse, DTD
from StringIO import StringIO

class TestSample(unittest.TestCase):
    """Unit tests for logsparser.normalize. Validate sample log example"""
    normalizer_path = os.environ['NORMALIZERS_PATH']

    def normalize_samples(self, norm, name, version):
        """Test logparser.normalize validate for syslog normalizer."""
        # open parser
        n = parse(open(os.path.join(self.normalizer_path, norm)))
        # validate DTD
        dtd = DTD(open(os.path.join(self.normalizer_path,
                                    'normalizer.dtd')))
        dtd.assertValid(n)
        # Create normalizer from xml definition
        normalizer = Normalizer(n, os.path.join(self.normalizer_path, 'common_tagTypes.xml'), os.path.join(self.normalizer_path, 'common_callBacks.xml'))
        self.assertEquals(normalizer.name, name)
        self.assertEquals(normalizer.version, version)
        self.assertTrue(normalizer.validate())

    def test_normalize_samples_001_syslog(self):
        self.normalize_samples('syslog.xml', 'syslog', 1.0)

    def test_normalize_samples_002_apache(self):
        self.normalize_samples('apache.xml', 'apache', 0.99)
    
    def test_normalize_samples_003_dhcpd(self):
        self.normalize_samples('dhcpd.xml', 'DHCPd', 0.99)
    
    def test_normalize_samples_004_lea(self):
        self.normalize_samples('LEA.xml', 'LEA', 0.99)
    
    def test_normalize_samples_005_netfilter(self):
        self.normalize_samples('netfilter.xml', 'netfilter', 0.99)
    
    def test_normalize_samples_006_pam(self):
        self.normalize_samples('pam.xml', 'PAM', 0.99)
    
    def test_normalize_samples_007_postfix(self):
        self.normalize_samples('postfix.xml', 'postfix', 0.99)
    
    def test_normalize_samples_008_squid(self):
        self.normalize_samples('squid.xml', 'squid', 0.99)
    
    def test_normalize_samples_009_sshd(self):
        self.normalize_samples('sshd.xml', 'sshd', 0.99)
    
    def test_normalize_samples_010_named(self):
        self.normalize_samples('named.xml', 'named', 0.99)
    
    def test_normalize_samples_011_named2(self):
        self.normalize_samples('named-2.xml', 'named-2', 0.99)
    
    def test_normalize_samples_012_symantec(self):
        self.normalize_samples('symantec.xml', 'symantec', 0.99)
    
    def test_normalize_samples_013_msexchange2007MTL(self):
        self.normalize_samples('MSExchange2007MessageTracking.xml', 'MSExchange2007MessageTracking', 0.99)

    def test_normalize_samples_014_arkoonfast360(self):
        self.normalize_samples('arkoonFAST360.xml', 'arkoonFAST360', 0.99)

    def test_normalize_samples_015_s3(self):
        self.normalize_samples('s3.xml', 's3', 0.99)

    def test_normalize_samples_016_snare(self):
        self.normalize_samples('snare.xml', 'snare', 1.0)

    def test_normalize_samples_017_vmware(self):
        self.normalize_samples('VMWare_ESX4-ESXi4.xml', 'VMWare_ESX4-ESXi4', 0.99)

#    def test_normalize_samples_018_mysql(self):
#        self.normalize_samples('mysql.xml', 'mysql', 0.99)

    def test_normalize_samples_019_IIS(self):
        self.normalize_samples('IIS.xml', 'IIS', 0.99)

    def test_normalize_samples_020_fail2ban(self):
        self.normalize_samples('Fail2ban.xml', 'Fail2ban', 0.99)
        
    def test_normalize_samples_021_GeoIPsource(self):
        try:
            import GeoIP #pyflakes:ignore
            self.normalize_samples('GeoIPsource.xml', 'GeoIPsource', 0.99)
        except ImportError:
            # cannot test
            pass

    def test_normalize_samples_022_URL_parsers(self):
        self.normalize_samples('URLparser.xml', 'URLparser', 0.99)
        self.normalize_samples('RefererParser.xml', 'RefererParser', 0.99)
    
    def test_normalize_samples_023_bitdefender(self):
        self.normalize_samples('bitdefender.xml', 'bitdefender', 0.99)

    def test_normalize_samples_024_denyall_traffic(self):
        self.normalize_samples('deny_traffic.xml', 'deny_traffic', 0.99)

    def test_normalize_samples_025_denyall_event(self):
        self.normalize_samples('deny_event.xml', 'deny_event', 0.99)

    def test_normalize_samples_026_xferlog(self):
        self.normalize_samples('xferlog.xml', 'xferlog', 0.99)

    def test_normalize_samples_027_wabauth(self):
        self.normalize_samples('wabauth.xml', 'wabauth', 0.99)

    def test_normalize_samples_028_dansguardian(self):
        self.normalize_samples('dansguardian.xml', 'dansguardian', 0.99)

    def test_normalize_samples_029_cisco_asa_header(self):
        self.normalize_samples('cisco-asa_header.xml', 'cisco-asa_header', 0.99)

    def test_normalize_samples_030_cisco_asa_msg(self):
        self.normalize_samples('cisco-asa_msg.xml', 'cisco-asa_msg', 0.99)

    def test_normalize_samples_031_openLDAP(self):
        self.normalize_samples('openLDAP.xml', 'openLDAP', 0.99)

    def test_normalize_samples_031_openLDAP_extras(self):
        self.normalize_samples('openLDAP-extras.xml', 'openLDAP-extras', 0.99)
        
    def test_normalize_samples_032_squidguard(self):
        self.normalize_samples('squidguard.xml', 'squidguard', 0.99)
        
    def test_normalize_samples_033_eventlogW2003(self):
        self.normalize_samples('eventlog_security_audit_windows2003_en.xml', 'EventLog-Security-Windows2003[EN]_1', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2003_en_2.xml', 'EventLog-Security-Windows2003[EN]_2', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2003_en_3.xml', 'EventLog-Security-Windows2003[EN]_3', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2003_en_4.xml', 'EventLog-Security-Windows2003[EN]_4', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2003_fr.xml', 'EventLog-Security-Windows2003[FR]_1', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2003_fr_2.xml', 'EventLog-Security-Windows2003[FR]_2', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2003_fr_3.xml', 'EventLog-Security-Windows2003[FR]_3', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2003_fr_4.xml', 'EventLog-Security-Windows2003[FR]_4', 0.99)

    def test_normalize_samples_034_msexchange2003MTL(self):
        self.normalize_samples('MSExchange2003MessageTracking.xml', 'MSExchange2003MessageTracking', 0.99)

    def test_normalize_samples_035_msexchange2003ISMailboxStore(self):
        self.normalize_samples('MSExchange2003ISMailboxStore.xml', 'MSExchangeIS Mailbox Store [2003-EN]', 0.99)
        self.normalize_samples('MSExchange2003ISMailboxStoreFR.xml', 'MSExchangeIS Mailbox Store [2003-FR]', 0.99)
    
    def test_normalize_samples_036_eventlogW2008(self):
        self.normalize_samples('eventlog_security_audit_windows2008_en.xml', 'EventLog-Security-Windows2008[EN]_1', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2008_en_2.xml', 'EventLog-Security-Windows2008[EN]_2', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2008_fr.xml', 'EventLog-Security-Windows2008[FR]_1', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2008_fr_2.xml', 'EventLog-Security-Windows2008[FR]_2', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2008_en_3.xml', 'EventLog-Security-Windows2008[EN]_3', 0.99)
        self.normalize_samples('eventlog_security_audit_windows2008_fr_3.xml', 'EventLog-Security-Windows2008[FR]_3', 0.99)
        
    def test_normalize_samples_037_wabObject(self):
        self.normalize_samples('wabObjects.xml', 'wabObject', 0.99)

class TestCSVPattern(unittest.TestCase):
    """Test CSVPattern behaviour"""
    normalizer_path = os.environ['NORMALIZERS_PATH']
   
    tt1 = TagType(name='Anything', ttype=str, regexp='.*')

    tt2 = TagType(name='SyslogDate', ttype=datetime,
                  regexp='[A-Z][a-z]{2} [ 0-9]\d \d{2}:\d{2}:\d{2}')
        
    tag_types = {}
    for tt in (tt1, tt2):
        tag_types[tt.name] = tt

    generic_tagTypes = get_generic_tagTypes(path = os.path.join(normalizer_path,
                                                 'common_tagTypes.xml'))

    cb_syslogdate = CallbackFunction("""
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
now = datetime.now()
currentyear = now.year
# Following line may throw a lot of ValueError
newdate = datetime(currentyear,
                   MONTHS.index(value[0:3]) + 1,
                   int(value[4:6]),
                   int(value[7:9]),
                   int(value[10:12]),
                   int(value[13:15]))
log["date"] = newdate
""", name = 'formatsyslogdate')

    def test_normalize_csv_pattern_001(self):
        t1 = Tag(name='date',
                tagtype = 'Anything',
                substitute = 'DATE')
        t2 = Tag(name='id',
                tagtype = 'Anything',
                substitute = 'ID')
        t3 = Tag(name='msg',
                tagtype = 'Anything',
                substitute = 'MSG')

        p_tags = {}
        for t in (t1, t2, t3):
            p_tags[t.name] = t

        p = CSVPattern('test', 'DATE,ID,MSG', tags = p_tags, tagTypes = self.tag_types, genericTagTypes = self.generic_tagTypes)
        ret = p.normalize('Jul 18 08:55:35,83,"start listening on 127.0.0.1, pam auth started"')
        self.assertEqual(ret['date'], 'Jul 18 08:55:35')
        self.assertEqual(ret['id'], '83')
        self.assertEqual(ret['msg'], 'start listening on 127.0.0.1, pam auth started')
        
    def test_normalize_csv_pattern_002(self):
        t1 = Tag(name='date',
                tagtype = 'SyslogDate',
                substitute = 'DATE')
        t2 = Tag(name='id',
                tagtype = 'Anything',
                substitute = 'ID')
        t3 = Tag(name='msg',
                tagtype = 'Anything',
                substitute = 'MSG')

        p_tags = {}
        for t in (t1, t2, t3):
            p_tags[t.name] = t
        
        p = CSVPattern('test', 'DATE,ID,MSG', tags = p_tags, tagTypes = self.tag_types, genericTagTypes = self.generic_tagTypes)

        ret = p.normalize('Jul 18 08:55:35,83,"start listening on 127.0.0.1, pam auth started"')
        self.assertEqual(ret['date'], 'Jul 18 08:55:35')
        self.assertEqual(ret['id'], '83')
        self.assertEqual(ret['msg'], 'start listening on 127.0.0.1, pam auth started')
            
        ret = p.normalize('2011 Jul 18 08:55:35,83,"start listening on 127.0.0.1, pam auth started"')
        self.assertEqual(ret, None)
        
    def test_normalize_csv_pattern_003(self):
        t1 = Tag(name='date',
               tagtype = 'SyslogDate',
               substitute = 'DATE',
               callbacks = ['formatsyslogdate'])
        t2 = Tag(name='id',
               tagtype = 'Anything',
               substitute = 'ID')
        t3 = Tag(name='msg',
               tagtype = 'Anything',
               substitute = 'MSG')

        p_tags = {}
        for t in (t1, t2, t3):
            p_tags[t.name] = t
        
        p = CSVPattern('test', 'DATE,ID,MSG', tags = p_tags,
                        tagTypes = self.tag_types, callBacks = {self.cb_syslogdate.name:self.cb_syslogdate},
                        genericTagTypes = self.generic_tagTypes)

        ret = p.normalize('Jul 18 08:55:35,83,"start listening on 127.0.0.1, pam auth started"')
        self.assertEqual(ret['date'], datetime(datetime.now().year, 7, 18, 8, 55, 35))
        self.assertEqual(ret['id'], '83')
        self.assertEqual(ret['msg'], 'start listening on 127.0.0.1, pam auth started')
    
    def test_normalize_csv_pattern_004(self):
        t1 = Tag(name='date',
                tagtype = 'Anything',
                substitute = 'DATE')
        t2 = Tag(name='id',
                tagtype = 'Anything',
                substitute = 'ID')
        t3 = Tag(name='msg',
                tagtype = 'Anything',
                substitute = 'MSG')

        p_tags = {}
        for t in (t1, t2, t3):
            p_tags[t.name] = t

        p = CSVPattern('test', ' DATE; ID ;MSG ', separator = ';', quotechar = '=', tags = p_tags, tagTypes = self.tag_types, genericTagTypes = self.generic_tagTypes)
        ret = p.normalize('Jul 18 08:55:35;83;=start listening on 127.0.0.1; pam auth started=')
        self.assertEqual(ret['date'], 'Jul 18 08:55:35')
        self.assertEqual(ret['id'], '83')
        self.assertEqual(ret['msg'], 'start listening on 127.0.0.1; pam auth started')
    
    def test_normalize_csv_pattern_005(self):
        t1 = Tag(name='date',
                tagtype = 'Anything',
                substitute = 'DATE')
        t2 = Tag(name='id',
                tagtype = 'Anything',
                substitute = 'ID')
        t3 = Tag(name='msg',
                tagtype = 'Anything',
                substitute = 'MSG')

        p_tags = {}
        for t in (t1, t2, t3):
            p_tags[t.name] = t

        p = CSVPattern('test', 'DATE ID MSG', separator = ' ', quotechar = '=', tags = p_tags, tagTypes = self.tag_types, genericTagTypes = self.generic_tagTypes)
        ret = p.normalize('=Jul 18 08:55:35= 83 =start listening on 127.0.0.1 pam auth started=')
        self.assertEqual(ret['date'], 'Jul 18 08:55:35')
        self.assertEqual(ret['id'], '83')
        self.assertEqual(ret['msg'], 'start listening on 127.0.0.1 pam auth started')
    
    def test_normalize_csv_pattern_006(self):
        t1 = Tag(name='date',
                tagtype = 'Anything',
                substitute = 'DATE')
        t2 = Tag(name='id',
                tagtype = 'Anything',
                substitute = 'ID')
        t3 = Tag(name='msg',
                tagtype = 'Anything',
                substitute = 'MSG')

        p_tags = {}
        for t in (t1, t2, t3):
            p_tags[t.name] = t

        p = CSVPattern('test', 'DATE ID MSG', separator = ' ', quotechar = '=', tags = p_tags, tagTypes = self.tag_types, genericTagTypes = self.generic_tagTypes)
        # Default behaviour of csv reader is doublequote for escape a quotechar.
        ret = p.normalize('=Jul 18 08:55:35= 83 =start listening on ==127.0.0.1 pam auth started=')
        self.assertEqual(ret['date'], 'Jul 18 08:55:35')
        self.assertEqual(ret['id'], '83')
        self.assertEqual(ret['msg'], 'start listening on =127.0.0.1 pam auth started')


class TestCommonElementsPrecedence(unittest.TestCase):
    """Unit test used to validate that callbacks defined in a normalizer
    take precedence over common callbacks."""

    normalizer_path = os.environ['NORMALIZERS_PATH']
    fake_syslog = StringIO("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE normalizer SYSTEM "normalizer.dtd">
<normalizer name="syslog"
            version="0.99"
            unicode="yes"
            ignorecase="yes"
            matchtype="match"
            appliedTo="raw">
 <description>
  <localized_desc language="en">Uh</localized_desc>
  <localized_desc language="fr">Ah</localized_desc>
 </description>
 <authors>
  <author>mhu@wallix.com</author>
 </authors>
<tagTypes>
  <tagType name="MACAddress" type="basestring">
   <description>
    <localized_desc language="en">Oh</localized_desc>
    <localized_desc language="fr">Eh</localized_desc>
   </description>
   <regexp>\d{1,3}</regexp>
  </tagType>
 </tagTypes>
 <callbacks>
  <callback name="MMM dd hh:mm:ss">
log["TEST"] = "TEST"
  </callback>
 </callbacks>
 <patterns>
  <pattern name="syslog-001">
   <description>
    <localized_desc language="en">Hoo</localized_desc>
    <localized_desc language="fr">Hi</localized_desc>
   </description>
   <text>MYMAC MYWHATEVER</text>
   <tags>
    <tag name="mac" tagType="MACAddress">
     <description>
      <localized_desc language="en">the log's priority</localized_desc>
      <localized_desc language="fr">urrrh</localized_desc>
     </description>
     <substitute>MYMAC</substitute>
    </tag>
    <tag name="__whatever" tagType="Anything">
     <description>
     <localized_desc language="en">the log's date</localized_desc>
     <localized_desc language="fr">bleeeh</localized_desc></description>
     <substitute>MYWHATEVER</substitute>
     <callbacks>
      <callback>MMM dd hh:mm:ss</callback>
     </callbacks>
    </tag>
   </tags>
   <examples>
    <example>
     <text>99 HERPA DERP</text>
     <expectedTags>
      <expectedTag name="mac">99</expectedTag>
      <expectedTag name="TEST">TEST</expectedTag>
     </expectedTags>
    </example>
   </examples>
  </pattern>
 </patterns>
</normalizer>""")
    n = parse(fake_syslog)

    def test_00_validate_fake_syslog(self):
        """Validate the fake normalizer"""
        dtd = DTD(open(os.path.join(self.normalizer_path,
                                    'normalizer.dtd')))
        self.assertTrue(dtd.validate(self.n))
        
    def test_10_common_elements_precedence(self):
        """Testing callbacks priority"""
        normalizer = Normalizer(self.n, 
                                os.path.join(self.normalizer_path, 'common_tagTypes.xml'), 
                                os.path.join(self.normalizer_path, 'common_callBacks.xml'))
        self.assertTrue(normalizer.validate())


class TestFinalCallbacks(unittest.TestCase):
    """Unit test used to validate FinalCallbacks"""

    normalizer_path = os.environ['NORMALIZERS_PATH']
    fake_syslog = StringIO("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE normalizer SYSTEM "normalizer.dtd">
<normalizer name="syslog"
            version="0.99"
            unicode="yes"
            ignorecase="yes"
            matchtype="match"
            appliedTo="raw">
 <description>
  <localized_desc language="en">Uh</localized_desc>
  <localized_desc language="fr">Ah</localized_desc>
 </description>
 <authors>
  <author>mhu@wallix.com</author>
 </authors>
<tagTypes>
  <tagType name="blop" type="basestring">
   <description>
    <localized_desc language="en">Oh</localized_desc>
    <localized_desc language="fr">Eh</localized_desc>
   </description>
   <regexp>[a-zA-Z]</regexp>
  </tagType>
 </tagTypes>
 <callbacks>
  <callback name="toto">
log["toto"] = log["a"] + log["b"]
  </callback>
  <callback name="tata">
if not value:
    log["tata"] = log["toto"] * 2
else:
    log["tata"] = log["toto"] * 3
  </callback>
  <callback name="tutu">
log['b'] = value * 2
  </callback>
 </callbacks>
 <patterns>
  <pattern name="syslog-001">
   <description>
    <localized_desc language="en">Hoo</localized_desc>
    <localized_desc language="fr">Hi</localized_desc>
   </description>
   <text>A B C</text>
   <tags>
    <tag name="a" tagType="blop">
     <description>
      <localized_desc language="en">the log's priority</localized_desc>
      <localized_desc language="fr">urrrh</localized_desc>
     </description>
     <substitute>A</substitute>
    </tag>
    <tag name="__b" tagType="blop">
     <description>
     <localized_desc language="en">the log's date</localized_desc>
     <localized_desc language="fr">bleeeh</localized_desc></description>
     <substitute>B</substitute>
     <callbacks>
      <callback>tutu</callback>
     </callbacks>
    </tag>
    <tag name="c" tagType="blop">
     <description>
      <localized_desc language="en">the log's priority</localized_desc>
      <localized_desc language="fr">urrrh</localized_desc>
     </description>
     <substitute>C</substitute>
    </tag>
   </tags>
   <examples>
    <example>
     <text>a b c</text>
     <expectedTags>
      <expectedTag name="a">a</expectedTag>
      <expectedTag name="b">bb</expectedTag>
      <expectedTag name="c">c</expectedTag>
      <expectedTag name="toto">abb</expectedTag>
      <expectedTag name="tata">abbabb</expectedTag>
     </expectedTags>
    </example>
   </examples>
  </pattern>
 </patterns>
 <finalCallbacks>
    <callback>toto</callback>
    <callback>tata</callback>
 </finalCallbacks>
</normalizer>""")
    n = parse(fake_syslog)

    def test_00_validate_fake_syslog(self):
        """Validate the fake normalizer"""
        dtd = DTD(open(os.path.join(self.normalizer_path,
                                    'normalizer.dtd')))
        self.assertTrue(dtd.validate(self.n))

    def test_10_final_callbacks(self):
        """Testing final callbacks"""
        normalizer = Normalizer(self.n, 
                                os.path.join(self.normalizer_path, 'common_tagTypes.xml'), 
                                os.path.join(self.normalizer_path, 'common_callBacks.xml'))
        self.assertTrue(['toto', 'tata'] == normalizer.finalCallbacks)
        self.assertTrue(normalizer.validate())


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_norm_chain_speed
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

import os
import timeit
from logsparser.lognormalizer import LogNormalizer

if __name__ == "__main__":
    path = os.environ['NORMALIZERS_PATH']
    ln = LogNormalizer(path)

    def test():
        l = {'raw' : "<29>Jul 18 08:55:35 naruto squid[3245]: 1259844091.407    307 82.238.42.70 TCP_MISS/200 1015 GET http://www.ietf.org/css/ietf.css fbo DIRECT/64.170.98.32 text/css" }
        l = ln.uuidify(l)
        ln.normalize(l)
    
    print "Testing speed ..."
    t = timeit.Timer("test()", "from __main__ import test")
    speed = t.timeit(100000)/100000
    print "%.2f microseconds per pass, giving a theoretical speed of %i logs/s." % (speed * 1000000, 1 / speed) 
    
    print "Testing speed with minimal normalization ..."
    ln.set_active_normalizers({'syslog' : True})
    ln.reload()
    t = timeit.Timer("test()", "from __main__ import test")
    speed = t.timeit(100000)/100000
    print "%.2f microseconds per pass, giving a theoretical speed of %i logs/s." % (speed * 1000000, 1 / speed)

########NEW FILE########
__FILENAME__ = test_suite
# -*- python -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

""" The LogNormalizer need to be instanciated with the path to
normalizers XML definitions.

Tests expects to find normlizer path in NORMALIZERS_PATH environment variable.

$ NORMALIZERS_PATH=normalizers/ python tests/test_suite.py
"""

import unittest
import test_normalizer
import test_lognormalizer
import test_log_samples
import test_commonElements
import test_extras

tests = (test_commonElements,
         test_normalizer,
         test_lognormalizer,
         test_log_samples,
         test_extras,
         )

load = unittest.defaultTestLoader.loadTestsFromModule
suite = unittest.TestSuite(map(load, tests)) 

unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
__FILENAME__ = orphan_tags
# -*- python -*-
# -*- coding: utf-8 -*-

# pylogsparser - Logs parsers python library
#
# Copyright (C) 2011 Wallix Inc.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#

"""Utility to visualize tags per taxonomy."""



import time
import os
from sys import exit as sysexit
from logsparser.lognormalizer import LogNormalizer as LN
from optparse import OptionParser

normalizer_path = os.environ['NORMALIZERS_PATH'] or '../normalizers/'

ln = LN(normalizer_path)

help = """
This utility aims to list tags frequencies per taxonomy.

It uses the environment variable $NORMALIZERS_PATH as the source of normalizers
to test.
By default, this script will use the sample logs shipped in the normalizers as
its input; it is possible to use another log file by using the parameter -i.

The script's output is a classification of tags per service type. It looks like
this:

Category *SERVICENAME* (N log(s)):

	* tag1 : 16.67%
		( program : 100.00%  )
	* tag2 : 16.67%
		( program : 100.00%  )
	...
	
N is the total amount of logs in the input set (sample logs included) that
match this category.
For each tag, the occurrence percentage is displayed; on the following line
the repartition of the logs with this tag, in this category, per program, is
displayed.
"""

parser = OptionParser(help)
parser.add_option("-i", 
                  "--input", 
                  dest="input", 
                  action="store", 
                  help="the path to an optional log source file")
(options, args) = parser.parse_args()

logs = []

if options.input:
    try:
        logs = open(options.input, 'r').readlines()
    except IOError, e:
        print "Could not open %s, skipping" % options.input
if not logs:
    print "Using default logs only."
    
categories = dict([ (u.taxonomy, 0) 
                    for u in sum(ln.normalizers.values(), [])
                    if u.taxonomy ]).keys()
categories.sort()
categories.append("N/A")
base_logs = [ e.raw_line for e in sum([ p.examples 
                                    for p in sum([ u.patterns.values() 
                                    for u in sum(ln.normalizers.values(), [])
                                    if u.appliedTo in ["raw", "body"] ], [])
                                  ], []) 
            ]

logs_per_categories = {}

def compute(logs_set):
    global logs_per_categories
    for l in logs_set:
        testlog = {'raw' : l,
                   'body': l}
        ln.lognormalize(testlog)
        taxonomy = testlog.get('taxonomy', "N/A")
        if taxonomy not in logs_per_categories:
            logs_per_categories[taxonomy] = {'logs' : 0,
                                             'tags' : {}
                                            }
        logs_per_categories[taxonomy]['logs'] += 1
        for t in testlog:
            if t not in logs_per_categories[taxonomy]['tags']:
                logs_per_categories[taxonomy]['tags'][t] = {'_total' : 0}
            prg = "Not set"
            if "program" in testlog:
                prg = testlog['program']
            if prg not in logs_per_categories[taxonomy]['tags'][t]:
                logs_per_categories[taxonomy]['tags'][t][prg] = 0
            logs_per_categories[taxonomy]['tags'][t]['_total'] += 1
            logs_per_categories[taxonomy]['tags'][t][prg] += 1

print "Parsing %i logs..." % (len(base_logs) + len(logs)),
start = time.time()
compute(base_logs)
compute(logs)
print "Done in %.2f seconds." % (time.time() - start)
print "\n-------------------\n"

for c in categories:
    if c in logs_per_categories:
        total = float(logs_per_categories[c]['logs'])
        print "Category %s (%i log(s)):\n" % (c, total)
        for t in sorted(logs_per_categories[c]['tags'].keys(), 
                        cmp = lambda x,y: cmp(logs_per_categories[c]['tags'][x]['_total'],
                                              logs_per_categories[c]['tags'][y]['_total'])
                       ):
            print "\t* %s : %.2f%%" % (t, 100 * logs_per_categories[c]['tags'][t]['_total'] / total)
            print "\t\t(",
            for prg in [ u for u in logs_per_categories[c]['tags'][t] if u is not '_total' ]:
                print "%s : %.2f%% " % (prg, 100 * float(logs_per_categories[c]['tags'][t][prg]) / logs_per_categories[c]['tags'][t]['_total']),
            print ")"
    else:
        print "No logs for category %s !" % c
    print "\n-------------------\n"
        

########NEW FILE########
__FILENAME__ = time_norm_va
# -*- python -*-
#
# time_norm_va.py
#
# Copyright (C) 2012 JF Taltavull - jftalta@gmail.com
#
# This program is part of pylogsparser, a logs parser python library, copyright (c) 2011 Wallix Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by the
# Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
#
# Description
# ===========
# This program aims to measure the validation time of each normalizer shipped with pylogsparser package.
# - the measure is done by applying the "normalizer.validate" method on each xml coded normalizer, assuming each
#   normalizer embeds at least one example.
# - the environment variable NORMALIZERS_PATH must be defined.
# - default iterations number per normalizer is 5000 (see "iterations" variable)
# - results are printed on standard output, sorted on time, ascending order (faster normalizer first).
# - times are in micro-seconds
#

import os
import sys
import re
import timeit
from logsparser.normalizer import Normalizer
from logsparser.lognormalizer import LogNormalizer
from lxml.etree import parse, DTD

"""Measuring normalizers validation time"""

VERSION = 0.99
iterations = 5000
excl = (                      # Exclusion list, skip these files
        "common_callBacks.xml",
        "common_tagTypes.xml",
        "normalizer.dtd",
        "normalizer.template"
       )
path = os.environ['NORMALIZERS_PATH']
norm = None                   # normalizer object
ln = LogNormalizer(path)
tested_logs = None

class res:

    def __init__(self, it):
        self.nn = 0       # number of normalizers
        self.ts = 0.0     # times sum
        self.it = it      # number of iterations per normalizer
        self.rl = []      # results list (a list of dictionaries)

    def add_res(self, n, v, a, s):
        self.rl.append({"name" : n, "version" : v, "author" : a, "time" : s});
        self.nn += 1
        self.ts += s

    def key_time(self, r):  # function used by sort method
        return r["time"]	# sort on time field, ascending order

    def print_result(self):
        i = 0
        self.rl.sort(key=self.key_time)
        for r in self.rl:
            i += 1
            print "%i - " % i, "%s" % r["name"], "t=%imis" % ((r["time"] / self.it) * 1000000),\
                  "(v%s" % r["version"], "%s)" % r["author"]
        print "Number of iterations per normalizer=%i" % self.it
        print "Average time per iteration=%imis" % (self.ts / (self.nn * self.it) * 1000000)


def validate_norm(fn, nn, version, it):
    global norm 
    global result

    # open XML parser
    n = parse(open(os.path.join(path, fn)))
    # validate DTD
    dtd = DTD(open(os.path.join(path, 'normalizer.dtd')))
    assert dtd.validate(n) == True
    # Create normalizer from xml definition
    norm = Normalizer(n, os.path.join(path, 'common_tagTypes.xml'),
                      os.path.join(path, 'common_callBacks.xml'))
    # Time normalizer validation
    try:
        assert norm.name.lower() == nn.lower()
        if norm.name != nn:
            print "Warning, %s has name attribute set to %s" % (fn, norm.name)
    except AssertionError:
        print "\n[%s]" % norm.name, "and [%s]" % nn, "don't match"
        return
    try:
        assert norm.version == version
    except AssertionError:
        print "\n[%s]" % norm.version, "and [%s]" % version, "don't match"
        return
    samples_amount = len([u for u in [v.examples for v in norm.patterns.values()]])
    if samples_amount <= 0:
        print "No samples to validate in %s" % fn
        return
    t = timeit.Timer("assert norm.validate() == True", "from __main__ import norm")
    s = t.timeit(it)
    # Normalize result against number of validated samples
    s = s / float(samples_amount)
    # Add result
    result.add_res(norm.name, norm.version, norm.authors, s)

def bench_full(it, logset = []):
    """@param logset : a list of logs to use for the speed test. Default
    behavior is to use log samples from patterns of normalizers that are applied
    to "raw" or "body" tags."""
    global ln
    global tested_logs
    results = []
    if not logset:
        norm_samples = ln.normalizers['raw'] + ln.normalizers['body']
        logset = [u.raw_line 
                  for u in sum([p.examples 
                                for p in sum([norm.patterns.values() 
                                              for norm in norm_samples], 
                                             []) ], 
                               [])
                 ]
    # first, classify logs per programs (or taxonomy ?)
    sorted_logset = {}
    print "Sorting logs ...",
    for logline in logset:
        d = {'raw' : logline,
             'body': logline }
        ln.normalize(d)
        if 'program' not in d:
            d['program'] = "Unknown program"
        sorted_logset[d['program']] = sorted_logset.get(d['program'], []) + [{'raw' : logline,
                                                                              'body': logline },]
    print " Done."
    # then, test logs per program:
    for program in sorted(sorted_logset.keys()):
        print "Testing %s logs ..." % program
        tested_logs = sorted_logset[program]
        t = timeit.Timer("""for l in tested_logs: ln.normalize(l)""",
                         """from __main__ import tested_logs, ln""")
        s = t.timeit(it) / float(len(tested_logs))
        results.append({'program' : program,
                        'time'    : s})
    # finally, show results
    print "Printing results:"
    i = 0
    avg_time = 0
    for line in sorted(results, key=lambda x: x['time']):
        i += 1
        print "%s. %s logs treated in %i mis on average (%i sample logs used)" % (i, 
                                                                                  line['program'], 
                                                                                  (line['time'] / it) * 1000000,
                                                                                  len(sorted_logset[line['program']]))
        avg_time += line['time'] / it
    print "\nAverage parsing time : %i mis" % ((avg_time / i) * 1000000)
                

if __name__ == "__main__":

    result = res(iterations)      # results object

    # Iterate on normalizers and validate
    print "Measuring normalizers validation time: "
    for fn in os.listdir(path):
        if (fn not in excl):
            nn = re.sub(r'\.xml$', '', fn) # normalizer file name must end with .xml suffix
            validate_norm(fn, nn, VERSION, iterations)
            print ".",
            sys.stdout.flush()

    # Print results
    print "\nPrinting results:" 
    result.print_result()
    
    print "\n-----------------------\nTesting full normalization chain:"
    bench_full(iterations)
    

########NEW FILE########
