/* Copyright � 1979-1999 Udanax.com. All rights reserved.

* This code is licensed under the terms of The Udanax Open-Source License, 
* which contains precisely the terms of the X11 License.  The full text of 
* The Udanax Open-Source License can be found in the distribution in the file 
* license.html.  If this file is absent, a copy can be found at 
* http://udanax.xanadu.com/license.html and http://www.udanax.com/license.html
*/

/* putfe.d - Udanax output routines -  front end version */
/* as of Jul 12 19:00:00 */

#include "xanadu.h"
#include "requests.h"

FILE *logfile;
FILE *nulllog;
FILE *reallog;

FILE *febelog = NULL;
bool firstputforrequest;

#define WORDELIM '~'
#define TUMDELIM '.'
#define SPANFLAG 's'
#define VSPECFLAG 'v'
#define TEXTFLAG 't'
#define FAILFLAG '?'

/*#define xuputc(c,fd) putc ((c), (fd))*/

int xuputc(char c, FILE *fd)
{
        if (putc (c, fd) == EOF) {
		perror("xuputc");
		frontenddied();
	} else if (febelog && febelog != nulllog) {
		if (firstputforrequest)
			fprintf(febelog, "\nbe:\n");
		firstputforrequest = FALSE;
		putc (c, febelog);
	}

}


int xuputstring(char *string, FILE *fd)
{
        /*while (*string)
                xuputc (*string++, fd);*/
	fwrite(string, 1, strlen(string), fd);
}


int putnum(FILE *outfile, INT num)
{
  char digits[32];
  INT i;

        if (num == 0)
                xuputc ('0', outfile);
        else {
		if (num < 0) {
			num = -num;
			xuputc('-', outfile);
		}
                for (i = 0; num != 0;) {
                        digits[i++] = (char) (num % 10 +  (INT)'0');
                        num /= 10;
                }
		while (i > 0)
			xuputc(digits[--i], outfile);
        }
}


int sendresultoutput(typetask *taskptr)
{
/*  FILE *fd;
        fd = taskptr->outp;
        write (fd->_file, fd->_base, (INT) (fd->_ptr - fd->_base));
        fd->_ptr = fd->_base;
        fd->_cnt = BUFSIZ;
*/      fflush (taskptr->outp);
}

int error(typetask *taskptr, char *string)
{
        xuputstring (string, taskptr->errp);
}

int prompt(typetask *taskptr, char *string)
{
        xuputstring (string, taskptr->outp);
}

int putnumber(FILE *outfile, INT num)
{
        putnum (outfile, num);
        xuputc (WORDELIM, outfile);
}

int puttumbler(FILE *outfile, tumbler *tumblerptr)
{
  INT i, place;

        putnum (outfile, - tumblerptr->exp);
        place = NPLACES;
        do { --place;
        } while (place > 0 && tumblerptr->mantissa[place] == 0);
        for (i = 0; i <= place; ++i) {
                xuputc (TUMDELIM, outfile);
                putnum (outfile, (INT)tumblerptr->mantissa[i]);
        }
        xuputc (WORDELIM, outfile);
}

int putisa(typetask *taskptr, typeisa *isaptr)
{
        puttumbler (taskptr->outp, isaptr);
}

int putitemset(typetask *taskptr, typeitemset itemset)
{
  INT i;
  typeitemset temp;

        for (temp = itemset, i = 0; temp; temp = (typeitemset)((typeitemheader *)temp)->next, ++i) {
                        while (((typeitemheader *)temp)->itemid == TEXTID && ((typeitemheader *)temp)->next && ((typeitemheader *)temp)->next->itemid == TEXTID)
                                temp = (typeitemset)((typeitemheader *)temp)->next; /* count lots of textitems as one item */
        }
        putnumber (taskptr->outp, i);
/* fprintf (taskptr->errp, "X putitemset  nitems is %d\n", i); */
        for (; itemset; itemset = (typeitemset)((typeitemheader *)itemset)->next) {
                if (((typeitemheader *)itemset)->itemid == TEXTID)
                        puttextset (taskptr, (typetext**)&itemset);
                else
                        putitem (taskptr, itemset);
        }
}

int putitem(typetask *taskptr, typeitem *itemptr)
{
 FILE *outfile;

        outfile = taskptr->outp;
        switch (((typeitemheader *)itemptr)->itemid) {
          case ISPANID:
                xuputc (SPANFLAG, outfile);
                xuputc (WORDELIM, outfile);
                putspan (taskptr, (typespan*)itemptr);
                break;
          case VSPANID:
                putspan (taskptr, (typespan*)itemptr);
                break;
          case VSPECID:
                xuputc (VSPECFLAG, outfile);
                xuputc (WORDELIM, outfile);
                puttumbler (outfile, &((typevspec*)itemptr)->docisa);
                putitemset (taskptr, (typeitemset)((typevspec*)itemptr)->vspanset);
                break;
          case TEXTID:
/* fprintf (taskptr->errp, "X put text %d characters\n",itemptr->length); */
                puttext (taskptr, (typetext*)itemptr);
                break;
          case ADDRESSID:
/*
fprintf (taskptr->errp, "X put address ");
puttumbler (taskptr->errp, &itemptr->address);
fprintf(taskptr->errp, "\n");
*/
                puttumbler (outfile, &((typeaddress *)itemptr)->address);
                break;

          default:
                error (taskptr, "illegal item id for senditem");
                return;
        }
}

int putspan(typetask *taskptr, typespan *spanptr)
{
fprintf (logfile, "putspan\n");
        puttumbler(taskptr->outp, &spanptr->stream);
        puttumbler(taskptr->outp, &spanptr->width);
}

int puttextset(typetask *taskptr, typetext **textptrptr)
{
  typetext *textptr, *last;
  INT i;

        for (i = 0, textptr = *textptrptr; textptr && textptr->itemid == TEXTID; textptr = textptr->next) {
                i += textptr->length;
        }
        xuputc (TEXTFLAG, taskptr->outp);
        putnumber (taskptr->outp, i);
        last = NULL;
        for (textptr = *textptrptr; textptr && textptr->itemid == TEXTID; textptr = textptr->next) {
                for (i = 0; i < textptr->length; ++i)
                        xuputc (textptr->string[i], taskptr->outp);
                last = textptr;
        }
        *textptrptr = last;
}

int puttext(typetask *taskptr, typetext *textptr)
{
 INT i;
fprintf (logfile, "puttext\n");
/* fprintf (taskptr->errp, "X puttext %d characters\n", textptr->length); */
        xuputc (TEXTFLAG, taskptr->outp);
        putnumber (taskptr->outp, textptr->length);

/*        write (fileno(taskptr->outp), textptr->string, textptr->length); */
        for (i = 0; i < textptr->length; ++i)
                xuputc (textptr->string[i], taskptr->outp);
}


int putspanpairset(typetask *taskptr, typespanpairset spanpairset)
{
  typespanpair *ptr;
  INT n;

        for (n = 0, ptr = spanpairset; ptr; ++n, ptr = ptr->nextspanpair);
        putnumber (taskptr->outp, n);
        for (; spanpairset; spanpairset = spanpairset->nextspanpair)
                putspanpair (taskptr, spanpairset);
}

int putspanpair(typetask *taskptr, typespanpair *spanpair)
{
        puttumbler (taskptr->outp, &spanpair->stream1);
        puttumbler (taskptr->outp, &spanpair->stream2);
        puttumbler (taskptr->outp, &spanpair->widthofspan);
}


/* ---------------- top level put routines --------------- */

int putinsert(typetask *taskptr)
{
        putnumber (taskptr->outp, INSERT);
}

int putretrievedocvspanset(typetask *taskptr, typespanset *spansetptr)
{
        putnumber (taskptr->outp, RETRIEVEDOCVSPANSET);
        putitemset (taskptr, (typeitemset)*spansetptr);
}

int putcopy(typetask *taskptr)
{
        putnumber (taskptr->outp, COPY);
}

int putrearrange(typetask *taskptr)
{
        putnumber (taskptr->outp, REARRANGE);
}

int putcreatelink(typetask *taskptr, typeisa *istreamptr)
{
        putnumber (taskptr->outp, CREATELINK);
        putisa (taskptr, istreamptr);
}

int putretrievev(typetask *taskptr, typevstuffset *vstuffsetptr)
{
/* fprintf (taskptr->errp, "X putretrievev\n"); */
        putnumber (taskptr->outp, RETRIEVEV);
        putitemset (taskptr, (typeitemset)*vstuffsetptr);
}

int putfindnumoflinksfromtothree(typetask *taskptr, INT num)
{
        putnumber (taskptr->outp, FINDNUMOFLINKSFROMTOTHREE);
        putnumber (taskptr->outp, num);
}

int putfindlinksfromtothree(typetask *taskptr, typelinkset linkset)
{
fprintf (logfile, "putfindlinksfromtothree\n");
        putnumber (taskptr->outp, FINDLINKSFROMTOTHREE);
        putitemset (taskptr, (typeitemset)linkset);
}

int putfindnextnlinksfromtothree(typetask *taskptr, INT n, typelinkset nextlinkset)
{
/* fprintf (taskptr->errp, "X putfindnextnlinksfromtothree\n"); */
        putnumber (taskptr->outp, FINDNEXTNLINKSFROMTOTHREE);
        putitemset (taskptr, (typeitemset)nextlinkset);
}

/* historical trace */

int putshowrelationof2versions(typetask *taskptr, typespanpairset relation)
{
        putnumber (taskptr->outp, SHOWRELATIONOF2VERSIONS);
        putspanpairset (taskptr, relation);
}

int putcreatenewdocument(typetask *taskptr, typeisa *newdocisaptr)
{
/*
fprintf (taskptr->errp, "X new document created ");
puttumbler (taskptr->errp, newdocisaptr);
fprintf (taskptr->errp, "\n");
*/
        putnumber (taskptr->outp, CREATENEWDOCUMENT);
        putisa (taskptr, newdocisaptr);
}

int putdeletevspan(typetask *taskptr)
{
        putnumber (taskptr->outp, DELETEVSPAN);
}

int putcreatenewversion(typetask *taskptr, typeisa *newdocisaptr)
{
        putnumber (taskptr->outp, CREATENEWVERSION);
        putisa (taskptr, newdocisaptr);
}

int putretrievedocvspan(typetask *taskptr, typespan *vspanptr)
{
        putnumber (taskptr->outp, RETRIEVEDOCVSPAN);
        putspan (taskptr, vspanptr);
}

/* set debug */

/* disk exit */

/* show enfilades */

int putfollowlink(typetask *taskptr, typespecset specset)
{
        putnumber (taskptr->outp, FOLLOWLINK);
        putitemset (taskptr, (typeitemset)specset);
}

/* examine */

/* source unix command */

int putfinddocscontaining(typetask *taskptr, typeitemset addressset)
{
/* fprintf (taskptr->errp, "X putfinddocscontaining\n"); */
        putnumber (taskptr->outp, FINDDOCSCONTAINING);
        putitemset (taskptr, addressset);
}

int putretrieveendsets(typetask *taskptr, typespecset fromset, typespecset toset, typespecset threeset)
{
        putnumber (taskptr->outp, RETRIEVEENDSETS);
        putitemset (taskptr, (typeitemset)fromset);
        putitemset (taskptr, (typeitemset)toset);
        putitemset (taskptr, (typeitemset)threeset);
}

int putrequestfailed(typetask *taskptr)
{
/*gerror("putrequestfailed \n");*/
        xuputc (FAILFLAG, taskptr->outp);
}

int putxaccount(typetask *taskptr)
{
	putnumber(taskptr->outp, XACCOUNT);
}

int putcreatenode_or_account(typetask *taskptr, tumbler *tp)
{
	putnumber(taskptr->outp, CREATENODE_OR_ACCOUNT);
	puttumbler(taskptr->outp,tp);
}

int putopen(typetask *taskptr, tumbler *tp)
{
	putnumber(taskptr->outp, OPEN);
	puttumbler(taskptr->outp,tp);
}

int putclose(typetask *taskptr)
{
	putnumber(taskptr->outp,CLOSE);
}

int putquitxanadu(typetask *taskptr)
{
	putnumber(taskptr->outp,QUIT);
}
