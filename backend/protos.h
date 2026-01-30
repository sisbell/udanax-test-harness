/* protos.h - Function prototypes for compile-time type checking */

#ifndef PROTOS_H
#define PROTOS_H

/* ============================================================
 * SECTION 1: Functions that only need types from common.h
 * (tumbler, typetask, humber, HEADER, INT, bool, FILE)
 * ============================================================ */

/* Forward declaration for HEADER (defined in alloc.h) */
union header;
typedef union header HEADER;

/* alloc.c */
int lookatalloc(void);
int lookatalloc2(HEADER *abaseallocated);
int ffree(char *ap);
int xgrabmorecore(void);
int writeallocinfo(INT fd);

/* allocdebug.c */
int analyzeanddebug(char *ptr);
int statusofalloc(char *c);
int validallocthinge(char *ptr);

/* corediskin.c - section 1 protos that don't need complex types */
int initincorealloctables(void);

/* corediskout.c - section 1 protos */
int writeenfilades(void);

/* disk.c */
int closediskfile(void);
int diskflush(void);
void diskexit(void);

/* diskalloc.c - section 1 protos */
int diskallocexit(INT fd);
bool readallocinfo(INT fd);

/* entexit.c */
int init(bool safe);

/* fns.c */
int frontenddied(void);

/* genf.c */
INT qerror(char *message);

/* init.c */
int initmagicktricks(void);
int initheader(void);

/* queues.c */
int initqueues(void);

/* rcfile.c */
void processrcfile(void);

/* test.c */
int footumbler(char *msg, tumbler *tptr);
int dumptumbler(tumbler *tumblerptr);
int dumphexstuff(char *ptr);
int checkpointer(char *msg, char *ptr);
void testforreservedness(char *msg);
void dumpstate(typetask *taskptr);

/* putfe.c */
int putdumpstate(typetask *taskptr);

/* tumble.c */
int tumblerjustify(tumbler *tumblerptr);
int tumblercopy(tumbler *fromptr, tumbler *toptr);
int tumblermax(tumbler *aptr, tumbler *bptr, tumbler *cptr);
int functiontumbleradd(tumbler *aptr, tumbler *bptr, tumbler *cptr);
int tumblersub(tumbler *aptr, tumbler *bptr, tumbler *cptr);
int absadd(tumbler *aptr, tumbler *bptr, tumbler *cptr);
int strongsub(tumbler *aptr, tumbler *bptr, tumbler *cptr);
int weaksub(tumbler *aptr, tumbler *bptr, tumbler *cptr);
INT tumblerintdiff(tumbler *aptr, tumbler *bptr);
int tumblerincrement(tumbler *aptr, INT rightshift, INT bint, tumbler *cptr);
int prefixtumbler(tumbler *aptr, INT bint, tumbler *cptr);
int beheadtumbler(tumbler *aptr, tumbler *bptr);
INT nstories(tumbler *tumblerptr);
INT lastdigitintumbler(tumbler *tumblerptr);
INT tumblerlength(tumbler *tumblerptr);
bool tumblercheck(tumbler *ptr);
int tumblertruncate(tumbler *aptr, INT bint, tumbler *cptr);

/* tumble.c */
int docidandvstream2tumbler(tumbler *docid, tumbler *vstream, tumbler *tumbleptr);

/* tumbleari.c */
INT tumblerfixedtoptr(tumbler *ptr, humber p);
INT tumblerptrtofixed(humber p, tumbler *tptr);
UINT functionintof(humber h);
UINT functionlengthof(humber ptr);

/* usefull.c */
int checkspecandstringbefore(void);
int setmem(char *addr, unsigned count, char byte);

#endif /* PROTOS_H */

/* ============================================================
 * SECTION 2: Functions that need types from xanadu.h
 * (typeisa, typespan, typespanset, typeitem, etc.)
 * Only included if xanadu.h has been included
 * ============================================================ */

#ifdef typegranf  /* Defined in xanadu.h */
#ifndef PROTOS_XANADU_H
#define PROTOS_XANADU_H

/* bert.c */
int hashoftumbler(tumbler *tp);
int logbertmodified(tumbler *tp, int connection);
int dobertexit(int connection);
int checkforopen(tumbler *tp, int type, int connection);
int addtoopen(tumbler *tp, int connection, int created, int type);
int logaccount(tumbler *tp);
int deleteversion(tumbler *tp);

/* context.c */
int foo(char *msg);

/* do1.c */
bool docreatenewdocument(typetask *taskptr, typeisa *isaptr);
bool doretrievev(typetask *taskptr, typespecset specset, typevstuffset *vstuffsetptr);
bool doappend(typetask *taskptr, typeisa *docptr, typetextset textset);

/* do2.c */
int makehint(INT typeabove, INT typebelow, INT typeofatom, typeisa *isaptr, typehint *hintptr);
bool doopen(typetask *taskptr, tumbler *tp, tumbler *newtp, int type, int mode, int connection);
bool doclose(typetask *taskptr, tumbler *tp, int connection);

/* get1.c / get1fe.c */
bool gettumbler(typetask *taskptr, tumbler *tumblerptr);
bool getisa(typetask *taskptr, typeisa *isaptr);
bool getnumber(typetask *taskptr, INT *numptr);
bool getvsa(typetask *taskptr, tumbler *vsaptr);
bool getcutseq(typetask *taskptr, typecutseq *cutseqptr);
bool getaccount(typetask *taskptr, typeisa *accountptr);
bool getrequest(typetask *taskptr, typerequest *requestptr);
char pullc(typetask *taskptr);
int getcreatenewdocument(void);

/* get2.c / get2fe.c */
bool getspan(typetask *taskptr, typespan *spanptr, char id);
bool getspanset(typetask *taskptr, typespanset *spansetptr, char id);
bool getspecset(typetask *taskptr, typespecset *specsetptr);
bool gettextset(typetask *taskptr, typetextset *textsetptr);

/* granf1.c */
int fooitemset(char *msg, typeitemset iptr);

/* put.c / putfe.c */
int prompt(typetask *taskptr, char *string);
int error(typetask *taskptr, char *string);
int puttumbler(FILE *outfile, tumbler *tumblerptr);
int putnum(FILE *outfile, INT num);
int putitem(typetask *taskptr, typeitem *itemptr);
int putspan(typetask *taskptr, typespan *spanptr);
int puttext(typetask *taskptr, typetext *textptr);
int puttextset(typetask *taskptr, typetext **textptrptr);
int putspanpair(typetask *taskptr, typespanpair *spanpair);
int putcreatelink(typetask *taskptr, typeisa *istreamptr);
int putfollowlink(typetask *taskptr, typespecset specset);
int putretrievedocvspanset(typetask *taskptr, typespanset *spansetptr);
/* Bug 009 semantic fix: filter to text subspace (V >= 1.0) */
typevspanset filter_vspanset_to_text_subspace(typetask *taskptr, typevspanset vspanset);
void filter_specset_to_text_subspace(typetask *taskptr, typespecset specset);
int putretrievev(typetask *taskptr, typevstuffset *vstuffsetptr);
int putfindlinksfromtothree(typetask *taskptr, typelinkset linkset);
int putfindnumoflinksfromtothree(typetask *taskptr, INT num);
int putfindnextnlinksfromtothree(typetask *taskptr, INT n, typelinkset nextlinkset);
int putcreatenewdocument(typetask *taskptr, typeisa *newdocisaptr);
int putfinddocscontaining(typetask *taskptr, typeitemset addressset);
int putinsert(typetask *taskptr);
int putcopy(typetask *taskptr);
int putrearrange(typetask *taskptr);
int putrequestfailed(typetask *taskptr);
int sendresultoutput(typetask *taskptr);
int xuputstring(char *string, FILE *fd);
int putretrievedocvspan(typetask *taskptr, typespan *vspanptr);
int putshowrelationof2versions(typetask *taskptr, typespanpairset relation);
int putcreatenewversion(typetask *taskptr, typeisa *newdocisaptr);
int putretrieveendsets(typetask *taskptr, typespecset fromset, typespecset toset, typespecset threeset);
int putdeletevspan(typetask *taskptr);
int putxaccount(typetask *taskptr);
int putcreatenode_or_account(typetask *taskptr, tumbler *tp);
int putopen(typetask *taskptr, tumbler *tp);
int putclose(typetask *taskptr);
int putquitxanadu(typetask *taskptr);

/* socketbe.c */
INT open_sock(void);
int isthisusersdocument(tumbler *tp);
bool establishprotocol(FILE *inp, FILE *outp);

/* task.c */
int inittask(typetask *taskptr);
int tfree(typetask *taskptr);
int tfreeexplicit(typetask *taskptr, char *ptr);
int tfreeitemset(typetask *taskptr, typeitemset itemset);
INT *taskalloc(typetask *taskptr, INT nbytes);

/* test.c */
int foospan(char *msg, typespan *span);
int foospanset(char *msg, typespan *spanset);
int dumpspan(typespan *spanptr);
int dumpspanpairset(typespanpairset spanpairset);
int dumpitem(typeitem *itemptr);
int dumpitemset(typeitemset itemset);
char *enftypestring(INT type);

/* xumain.c */
int xanadu(typetask *taskptr);

/* correspond.c */
int copyspanset(typetask *taskptr, typespan *spanptr, typespan **newptrptr);
int makespanpairset(typetask *taskptr, typeispanset ispanset, typespecset specset1, typespecset specset2, typespanpairset *pairsetptr);
int makespanpairsforispan(typetask *taskptr, tumbler *iwidth, typespecset *specset1ptr, typespecset *specset2ptr, typespanpairset *pairsetptr);
int intersectlinksets(typetask *taskptr, typelinkset linkset1, typelinkset linkset2, typelinkset linkset3, typelinkset *linkset4ptr);
int removespansnotinoriginal(typetask *taskptr, typespecset original, typespecset *newptr);
int restrictspecsetsaccordingtoispans(typetask *taskptr, typeispanset ispanset, typespecset *specset1, typespecset *specset2);
int restrictvspecsetovercommonispans(typetask *taskptr, typeispanset ispanset, typespecset specset, typespecset *newspecsetptr);

/* test.c - prototypes that need xanadu.h types */
int checkitem(char *msg, typeitem *ptr);

#endif /* PROTOS_XANADU_H */
#endif /* typegranf */

/* ============================================================
 * SECTION 3: Functions that need types from enf.h
 * (typecuc, typecorecrum, typewid, typedsp, etc.)
 * Only included if enf.h has been included
 * ============================================================ */

#ifdef GRAN  /* Defined in enf.h */
#ifndef PROTOS_ENF_H
#define PROTOS_ENF_H

/* Forward declarations for types from coredisk.h and ndenf.h */
struct structfreediskentry;
typedef struct structfreediskentry freediskentry;
union uniondiskloaf;
typedef union uniondiskloaf typediskloaf;
struct structuberdiskloaf;
typedef struct structuberdiskloaf typeuberdiskloaf;
union unionuberrawdiskloaf;
typedef union unionuberrawdiskloaf typeuberrawdiskloaf;
struct structknives;
typedef struct structknives typeknives;

/* bert.c */
int logbertmodifiedforcrum(typecuc *crumptr, int connection);

/* context.c */
int dump(typecorecrum *ptr);
int contextfree(typecontext *context);
int crumcontextfree(typecrumcontext *context);
INT index2itemid(INT index, typecontext *context);

/* corediskin.c */
int inorglinternal(typecbc *granorglptr, typeuberrawdiskloaf *crumptr);

/* corediskout.c */
int subtreewrite(typecuc *father);
int orglwrite(typecbc *orglcbcptr);
int inloaf(typecuc *father);
int inorgl(typecbc *granorglptr);
int transferloaf(typecuc *from, typecuc *to);
int hputinfo(typecbc *ptr, char **loafptrptr);

/* credel.c */
int testforrejuvinate(typecorecrum *ptr);
int ivemodified(typecorecrum *ptr);
int adopt(typecorecrum *new, INT relative, typecorecrum *old);
int disown(typecorecrum *crumptr);
int disownnomodify(typecorecrum *crumptr);
int reap(typecorecrum *localreaper);
int grimlyreap(void);

/* disk.c */
int diskfree(typediskloafptrdigit loafptr);
INT changerefcount(typediskloafptr diskptr, INT delta);

/* diskalloc.c */
int addtofreediskstructures(freediskentry *diskentry);
int diskset(typediskloafptrdigit loafptr);
int dumpfreediskentry(freediskentry *ptr);
int dumpfdhashtable(void);
int dumpfdorderedtable(void);
INT fdhash(INT diskblocknumber);
int readpartialdiskalloctablefromdisk(void);
int savepartialdiskalloctabletodisk(void);
INT changeunterrefcount(typediskloaf *wholeloafp, char *originalloafp, INT delta);
INT numberofliveunterloafs(typeuberdiskloaf *loafp);

/* edit.c */
int expandcrumleftward(typecorecrum *crumptr, tumbler *newdsp, tumbler *base, INT index);
int slicecbcpm(typecorecrum *ptr, typewid *offset, typecorecrum *new, tumbler *cut, INT index);
INT rearrangecutsectionnd(typecorecrum *ptr, typewid *offset, typeknives *knives);
INT insertcutsectionnd(typecorecrum *ptr, typewid *offset, typeknives *knives);

/* genf.c */
int levelpush(typecuc *fullcrumptr);
int levelpull(typecuc *fullcrumptr);

/* granf2.c */
int findvsatoappend(typecorecrum *ptr, tumbler *vsaptr);
int findnextaddressinvspace(typecorecrum *crumptr, typewid *offsetptr, tumbler *nextvspacestartptr, tumbler *vsaptr);

/* insert.c */
int insertseq(typecuc *fullcrumptr, tumbler *address, typegranbottomcruminfo *info);

/* insertnd.c */
int insertnd(typetask *taskptr, typecuc *fullcrumptr, typewid *origin, typewid *width, type2dbottomcruminfo *infoptr, INT index);
INT doinsertnd(typecuc *father, typewid *origin, typewid *width, type2dbottomcruminfo *infoptr, INT index);
int makegappm(typetask *taskptr, typecuc *fullcrumptr, typewid *origin, typewid *width);
int findaddressofsecondcutforinsert(tumbler *position, tumbler *secondcut);
int firstinsertionnd(typecuc *father, typewid *origin, typewid *width, type2dbottomcruminfo *infoptr);
INT insertmorend(typecuc *father, typedsp *offset, typewid *origin, typewid *width, type2dbottomcruminfo *infoptr, INT index);
INT insertcbcnd(typecuc *father, typedsp *grasp, typewid *origin, typewid *width, type2dbottomcruminfo *infoptr);

/* ndcuts.c */
int makecutsnd(typecuc *fullcrumptr, typeknives *knives);
int makecutsdownnd(typecuc *fullcrumptr, typewid *offset, typeknives *knives);
int makecutsbackuptohere(typecuc *ptr, typewid *offset, typeknives *knives);
int cutsons(typecuc *ptr, typewid *offset, typeknives *knives);
int makeithcutonson(typecorecrum *ptr, typewid *offset, typecorecrum *son, typewid *grasp, typeknives *knives, INT i);
INT deletecutsectionnd(typecorecrum *ptr, typewid *offset, typeknives *knives);
int peeloffcorrectson(typecorecrum *ptr, typeknives *knives);
int peelsoncorrectly(typecorecrum *ptr, typewid *offset, typecorecrum *son, typewid *grasp, typeknives *knives, INT i);
int makeoffsetsfor3or4cuts(typeknives *knives, tumbler diff[]);
int sortknives(typeknives *knifeptr);

/* ndinters.c */
int newfindintersectionnd(typecuc *fullcrumptr, typeknives *knives, typecuc **ptrptr, typewid *offset);

/* multiloaf.c */
int addallocatedloaftopartialallocedtables(typediskloafptr dp, INT size);

/* recombine.c */
int recombine(typecuc *father);
int recombineseq(typecuc *father);
int recombinend(typecuc *father);
int takeovernephewsseq(typecorecrum *me);
int takeovernephewsnd(typecuc **meptr, typecuc **broptr);
int eatbrossubtreeseq(typecuc *me);
int getorderedsons(typecuc *father, typecorecrum *sons[]);
INT comparecrumsdiagonally(typecorecrum *a, typecorecrum *b);

/* retrie.c */
int prologuend(typecorecrum *ptr, typedsp *offset, typedsp *grasp, typedsp *reach);
int prologuecontextnd(typecontext *ptr, typedsp *grasp, typedsp *reach);
INT whereoncrum(typecorecrum *ptr, typewid *offset, tumbler *address, INT index);
INT whereoncontext(typecontext *ptr, tumbler *address, INT index);
int findcbcinspanseq(typecorecrum *crumptr, typewid *offsetptr, tumbler *spanstart, tumbler *spanend, typecontext **headptr);
int findcbcinarea2d(typecorecrum *crumptr, typedsp *offsetptr, tumbler *span1start, tumbler *span1end, INT index1, tumbler *span2start, tumbler *span2end, INT index2, typecontext **headptr, typebottomcruminfo *infoptr);
int oncontextlistseq(typecontext **clistptr, typecontext *c);
int incontextlistnd(typecontext **clistptr, typecontext *c, INT index);

/* split.c */
int splitcrum(typecuc *father);
int splitcrumseq(typecuc *father);
int splitcrumsp(typecuc *father);
int splitcrumpm(typecuc *father);
int peelcrumoffnd(typecorecrum *ptr);

/* test.c - prototypes that only need enf.h types */
int dumpcontext(typecontext *context);
int dumpcontextlist(typecontext *context);
int dumpdsp(typewid *dspptr, INT enftype);
int dumpwid(typewid *widptr, INT enftype);
int dumpsubtree(typecuc *father);
int dumpwholesubtree(typecuc *father);
int dumpwholetree(typecorecrum *ptr);
int dumppoomwisps(typecorecrum *orgl);
int checkwholesubtree(typecuc *father);
bool asserttreeisok(typecorecrum *ptr);
int displaycutspm(typeknives *knivesptr);

/* genf.c */
typecuc *functionweakfindfather(typecorecrum *ptr);

/* makeroom.c */
int makeroomonleftnd(typecuc *father, typedsp *offset, typewid *origin, typedsp *grasp);

/* ndcuts.c */
int newpeelcrumoffnd(typecorecrum *ptr, typecorecrum *newuncle);

/* test.c */
int foohex(char *msg, INT num);
int foocontext(char *msg, typecontext *context);
int foocontextlist(char *msg, typecontext *context);
int check(typecuc *ptr);

/* wisp.c */
int dspadd(typedsp *a, typewisp *b, typedsp *c, INT enftype);
int dspsub(typedsp *a, typewisp *b, typedsp *c, INT enftype);
int setwispupwards(typecuc *ptr, INT testflag);
int setwidnd(typecuc *father);
int didntchangewisps(void);
int lockadd(tumbler *lock1, tumbler *lock2, tumbler *lock3, unsigned loxize);
int locksubtract(tumbler *lock1, tumbler *lock2, tumbler *lock3, unsigned loxize);
int lockmin(tumbler *lock1, tumbler *lock2, tumbler *lock3, unsigned loxize);
int lockmax(tumbler *lock1, tumbler *lock2, tumbler *lock3, unsigned loxize);

#endif /* PROTOS_ENF_H */
#endif /* GRAN */

/* ============================================================
 * SECTION 4: Functions that need types from BOTH enf.h AND xanadu.h
 * (typecuc, typecorecrum from enf.h + typeisa, typesporglset, etc. from xanadu.h)
 * ============================================================ */

#if defined(GRAN) && defined(typegranf)
#ifndef PROTOS_ENF_XANADU_H
#define PROTOS_ENF_XANADU_H

/* orglinks.c */
int linksporglset2vspec(typetask *taskptr, typeisa *homedoc, typesporglset *sporglsetptr, typevspec *specptr, int type);
int sporglset2vspanset(typetask *taskptr, typeisa *homedoc, typesporglset *sporglsetptr, typevspanset *vspansetptr, int type);

/* sporgl.c */
int contextintosporgl(type2dcontext *context, tumbler *linkid, typesporgl *sporglptr, INT index);
int sporglset2linkset(typetask *taskptr, typecuc *spanfptr, typesporglset sporglset, typelinkset *linksetptr, typeispan *homeset, INT spantype);
int sporglset2linksetinrange(typetask *taskptr, typecuc *spanfptr, typesporglset sporglset, typelinkset *linksetptr, typeispan *orglrange, INT spantype);
int unpacksporgl(typesporglset sporglptr, tumbler *streamptr, tumbler *widthptr, type2dbottomcruminfo *infoptr);

/* context.c */
int context2vtext(typecontext *context, typeispan *ispanptr, typevstuffset vstuffset);
int context2span(typecontext *context, typespan *restrictionspanptr, INT idx1, typespan *foundspanptr, INT idx2);

/* granf2.c */
int findpreviousisagr(typecorecrum *crumptr, typeisa *upperbound, typeisa *offset);
int findlastisaincbcgr(typecbc *ptr, typeisa *offset);

/* edit.c */
int deletend(typecuc *fullcrumptr, tumbler *origin, tumbler *width, INT index);
int rearrangend(typecuc *fullcrumptr, typecutseq *cutseqptr, INT index);

/* orglinks.c */
int maxtextwid(typetask *taskptr, typecorecrum *crumptr, tumbler *voffset, typevspanset *maxwidptr);
int putvspaninlist(typetask *taskptr, typevspan *spanptr, typevspanset *spansetptr);

#endif /* PROTOS_ENF_XANADU_H */
#endif /* GRAN && typegranf */
