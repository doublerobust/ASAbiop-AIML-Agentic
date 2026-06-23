/* TC-015 Ground Truth: Kaplan-Meier Curve with Risk Table (SAS)
   Part of the ASA Biopharm AI/ML WG Agentic AI Benchmark

   ⚠️  REFERENCE IMPLEMENTATION ONLY — NOT RUN OR VERIFIED
   No SAS license available to execute this code.
   Ground truth established via R (survival::survfit) and Python (lifelines) only.

   Primary: PROC LIFETEST with ODS OUTPUT for curve coordinates and risk sets
   CONFTYPE=LOGLOG set explicitly to match R/Python CI method.

   Usage: sas tc-015-km-curve.sas -set seed 42 -set n 200 -set outpath .
*/

%let seed    = 42;
%let n       = 200;
%let outpath = .;

* ── Generate synthetic ADTTE data ──;
data adtte;
  call streaminit(&seed.);
  length trt01a $13 usubjid $8 sex $1;
  
  do i = 1 to &n.;
    if i <= &n. / 2 then do;
      trt01pn = 1;
      trt01a = "Experimental";
    end;
    else do;
      trt01pn = 0;
      trt01a = "Control";
    end;
    
    * Experimental: shape=1.3, scale=14; Control: shape=1.1, scale=8;
    * Gamma via: scale * (-log(1-U))^(1/shape);
    u = rand("UNIFORM");
    if trt01pn = 1 then tte = 14 * (-log(1 - u)) ** (1 / 1.3);
    else tte = 8 * (-log(1 - u)) ** (1 / 1.1);
    
    * Censoring: uniform 6–30;
    cens = 6 + 24 * rand("UNIFORM");
    
    if tte <= cens then do;
      aval = tte;
      evnt = 1;
      cnsr = 0;
    end;
    else do;
      aval = cens;
      evnt = 0;
      cnsr = 1;
    end;
    
    sex = ifc(rand("UNIFORM") < 0.5, "F", "M");
    ecog = ifc(rand("UNIFORM") < 0.6, 0, 1);
    
    usubjid = cats("SUB", put(i, z4.));
    aval = round(aval, 0.0001);
    
    output;
  end;
  
  keep usubjid trt01pn trt01a aval cnsr evnt sex ecog;
run;

* ── KM estimation by treatment arm ──;
* Use CONFTYPE=LOGLOG to match R survfit default CI method;
ods output ProductLimitEstimates=ple Quartiles=quartiles HomTests=homtests;
proc lifetest data=adtte conftype=loglog;
  time aval * cnsr(1);
  strata trt01pn;
run;
ods output close;

* ── Extract survival estimates at standard time points ──;
* Time points: 0, 3, 6, 9, 12, 15, 18, 21, 24, 30;
data curve_points;
  set ple;
  
  * Standard time points for risk table;
  array tps{10} (0 3 6 9 12 15 18 21 24 30);
  
  * Keep all PLE rows — we'll summarize at specific times;
  keep trt01pn aval survival conftype lower upper;
  
  rename aval = time;
run;

* ── Risk table: number at risk at each time point ──;
* PROC LIFETEST provides n_at_risk in the ProductLimitEstimates at each event time;
* For standard time points, we compute via DATA step merge;
data risk_table;
  set adtte;
  
  array tps{10} (0 3 6 9 12 15 18 21 24 30);
  
  do k = 1 to 10;
    tp = tps{k};
    if aval >= tp then do;
      n_at_risk = 1;
      output;
    end;
  end;
  
  keep trt01pn tp n_at_risk;
run;

proc sql;
  create table risk_summary as
  select trt01pn, tp, sum(n_at_risk) as n_at_risk
  from risk_table
  group by trt01pn, tp
  order by trt01pn, tp;
quit;

* ── Events at risk at each time point ──;
data event_table;
  set adtte;
  
  array tps{10} (0 3 6 9 12 15 18 21 24 30);
  
  do k = 1 to 10;
    tp = tps{k};
    tp_next = ifn(k < 10, tps{k+1}, 99999);
    
    * Events in interval (tp, tp_next];
    if tp < aval <= tp_next and evnt = 1 then do;
      n_events = 1;
      output;
    end;
  end;
  
  keep trt01pn tp n_events;
run;

proc sql;
  create table event_summary as
  select trt01pn, tp, sum(n_events) as n_events
  from event_table
  group by trt01pn, tp
  order by trt01pn, tp;
quit;

* ── Overall median survival ──;
ods output Quartiles=overall_quartiles;
proc lifetest data=adtte conftype=loglog;
  time aval * cnsr(1);
run;
ods output close;

* ── Log-rank test ──;
ods output HomTests=lr_result;
proc lifetest data=adtte;
  time aval * cnsr(1);
  strata trt01pn / test=logrank;
run;
ods output close;

* ── Event counts by arm ──;
proc sql;
  select count(*) into :n_total from adtte;
  select count(*) into :n_exp from adtte where trt01pn = 1;
  select count(*) into :n_ctl from adtte where trt01pn = 0;
  select sum(evnt) into :evt_exp from adtte where trt01pn = 1;
  select sum(evnt) into :evt_ctl from adtte where trt01pn = 0;
quit;

* ── Extract log-rank p-value ──;
data _null_;
  set lr_result;
  where Test = "Log-Rank";
  call symputx('lr_chisq', put(ChiSq, 8.4));
  call symputx('lr_df', put(DF, 2.0));
  call symputx('lr_p', put(ProbChiSq, 10.6));
run;

* ── Extract overall median ──;
data _null_;
  set overall_quartiles;
  where percent = 50;
  call symputx('median', ifc(missing(estimate), 'null', put(estimate, 6.4)));
  call symputx('med_lower', ifc(missing(lowerlimit), 'null', put(lowerlimit, 6.4)));
  call symputx('med_upper', ifc(missing(upperlimit), 'null', put(upperlimit, 6.4)));
run;

* ── Output JSON ──;
data _null_;
  file "&outpath./tc-015-output.json";
  put '{"test_case_id": "TC-015",';
  put '"language": "SAS",';
  put '"tc_name": "KM Curve with Risk Table",';
  put '"metadata": {';
  put '  "n_total": ' "&n_total.,";
  put '  "n_experimental": ' "&n_exp.,";
  put '  "n_control": ' "&n_ctl.,";
  put '  "events_experimental": ' "&evt_exp.,";
  put '  "events_control": ' "&evt_ctl.,";
  put '  "population": "ITT",';
  put '  "time_unit": "months",';
  put '  "time_points": [0, 3, 6, 9, 12, 15, 18, 21, 24, 30]';
  put '},';
  put '"overall_median": {';
  put '  "median": ' "&median.,";
  put '  "ci_lower": ' "&med_lower.,";
  put '  "ci_upper": ' "&med_upper.";
  put '},';
  put '"logrank": {';
  put '  "chisq": ' "&lr_chisq.,";
  put '  "df": ' "&lr_df.,";
  put '  "p_value": ' "&lr_p.";
  put '},';
  put '"ci_method": "log-log",';
  put '"method": "PROC LIFETEST"';
  put '}';
run;

title "TC-015: KM Curve with Risk Table (SAS)";
title2 "ITT Population | N=&n_total (Exp=&n_exp, Ctl=&n_ctl)";
proc print data=risk_summary noobs;
  by trt01pn;
  var tp n_at_risk;
  label tp="Time (months)" n_at_risk="N at risk";
run;
title;

title2 "Log-Rank Test: ChiSq=&lr_chisq, DF=&lr_df, p=&lr_p";
proc print data=lr_result noobs;
  var Test ChiSq DF ProbChiSq;
run;
title;
