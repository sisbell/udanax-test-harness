/* Copyright � 1979-1999 Udanax.com. All rights reserved.

* This code is licensed under the terms of The Udanax Open-Source License, 
* which contains precisely the terms of the X11 License.  The full text of 
* The Udanax Open-Source License can be found in the distribution in the file 
* license.html.  If this file is absent, a copy can be found at 
* http://udanax.xanadu.com/license.html and http://www.udanax.com/license.html
*/
/* get1.d - Udanax top-level input routines */
/* as of Jul 12 19:00:00 */

#include "xanadu.h"

bool getfinddocscontaining(typetask *taskptr, typespecset *specsetptr)
{
	return (getspecset (taskptr, specsetptr));
}


bool getcopy(typetask *taskptr, typeisa *docisaptr, typeisa *vsaptr, typespecset *localspecsetptr)
{
	prompt(taskptr, "copy to this document=> ");
	if (!getisa(taskptr, docisaptr))
		return(FALSE);
	prompt(taskptr, "at this address=> ");
	if ( !(getvsa(taskptr, vsaptr)
		&& getspecset(taskptr, localspecsetptr)))
			return(FALSE);
	return(TRUE);
}

bool getinsert(typetask *taskptr, tumbler *docisaptr, tumbler *vsaptr, typetextset *textsetptr)
{
	prompt(taskptr, "text=>\n\n");
	if (!gettextset(taskptr, textsetptr))
		return(FALSE);
	prompt(taskptr, "document=> " );
	if (!getisa(taskptr, docisaptr))
		return(FALSE);
	prompt(taskptr, "address=> ");
	if (!getvsa(taskptr, vsaptr))
		return(FALSE);
	return(TRUE);
}

bool getcreatelink(typetask *taskptr, typeisa *docisaptr, typespecset *fromspecsetptr, typespecset *tospecsetptr, typespecset *threespecsetptr)
{
	prompt (taskptr, "home document=> ");
	if (!getisa (taskptr, docisaptr))
		return (FALSE);
	prompt (taskptr, "fromset\n");
	if (!getspecset (taskptr, fromspecsetptr))
		return (FALSE);
	prompt (taskptr, "toset\n");
	if (!getspecset (taskptr, tospecsetptr))
		return (FALSE);
	prompt (taskptr, "threeset\n");
	if (!getspecset (taskptr, threespecsetptr))
		return (FALSE);
	return (TRUE);
}

bool getfollowlink(typetask *taskptr, typeisa *linkisaptr, INT *whichendptr)
{
	prompt (taskptr, "enter link=> ");
	if (!getisa (taskptr, linkisaptr))
		return (FALSE);
	prompt (taskptr, "enter endset=> ");
	if (!(
	   getnumber (taskptr, whichendptr)
	&& (*whichendptr == 1 || *whichendptr == 2 || *whichendptr == 3)))
		return (FALSE);
	return (TRUE);
}

bool getcreatenewversion(typetask *taskptr, typeisa *docisaptr)
{
	  prompt(taskptr,"enter document=> ");
	  return (getisa (taskptr, docisaptr));
}

bool getretrievedocvspanset(typetask *taskptr, typeisa *docisaptr)
{
	prompt(taskptr, "enter document=> ");
	return (getisa (taskptr, docisaptr));
}

bool getretrievedocvspan(typetask *taskptr, typeisa *docisaptr)
{
	prompt(taskptr, "enter document=> ");
	return (getisa (taskptr, docisaptr));
}

bool getrearrange(typetask *taskptr, typeisa *docisaptr, typecutseq *cutseqptr)
{
	prompt(taskptr, "enter document=> ");
	if (!getisa(taskptr, docisaptr))
		return(FALSE);
	prompt(taskptr, "enter cutseq=>\n");
	if (!getcutseq(taskptr, cutseqptr))
		return(FALSE);
	return(TRUE);
}

bool getretrievev(typetask *taskptr, typespecset *specsetptr)
{
	return getspecset(taskptr,specsetptr);
}

bool getfindlinksfromtothree(typetask *taskptr, typespecset *fromvspecsetptr, typespecset *tovspecsetptr, typespecset *threevspecsetptr, typeispanset *homesetptr)
{
	prompt (taskptr, "fromset\n");
	if (!getspecset (taskptr, fromvspecsetptr))
		return(FALSE);
	prompt (taskptr, "toset\n");
	if (!getspecset (taskptr, tovspecsetptr))
		return(FALSE);
	prompt (taskptr, "threeset\n");
	if (!getspecset (taskptr, threevspecsetptr))
		return (FALSE);
	prompt (taskptr, "home documents\n");
	if (!getspanset (taskptr, homesetptr, ISPANID))
		return (FALSE);
	return(TRUE);
}

bool getfindnumoflinksfromtothree(typetask *taskptr, typespecset *fromvspecsetptr, typespecset *tovspecsetptr, typespecset *threevspecsetptr, typeispanset *homesetptr)
{
	return (getfindlinksfromtothree (taskptr, fromvspecsetptr, tovspecsetptr, threevspecsetptr, homesetptr));
}

bool getfindnextnlinksfromtothree(typetask *taskptr, typespecset *fromvspecsetptr, typespecset *tovspecsetptr, typespecset *threevspecsetptr, typeispanset *homesetptr, typeisa *lastlinkptr, INT *nptr)
{
	if(!getfindlinksfromtothree (taskptr, fromvspecsetptr, tovspecsetptr, threevspecsetptr, homesetptr))
		return(FALSE);
	prompt(taskptr, "last link=> ");
	if(!getisa(taskptr, lastlinkptr))
		return(FALSE);
	prompt(taskptr, "number of links => ");
	if(!getnumber(taskptr, nptr))
		return(FALSE);
	return(TRUE);
}


/* getnavigateonht */

bool getshowrelationof2versions(typetask *taskptr, typespecset *version1ptr, typespecset *version2ptr)
{
	prompt(taskptr, "version1\n");
	if (!getspecset (taskptr,version1ptr))
		return(FALSE);
	prompt(taskptr, "version2\n");
	if (!getspecset (taskptr,version2ptr))
		return(FALSE);
	return(TRUE);
}
int getcreatenewdocument(void)
{
}

bool getdeletevspan(typetask *taskptr, typeisa *docisaptr, typevspan *vspanptr)
{
	prompt(taskptr, "document=> ");
	if(!getisa (taskptr,docisaptr))
		return(FALSE);
	prompt(taskptr, "delete this part\n");
	if(!getspan (taskptr,vspanptr,VSPANID/*zzz*/))
		return(FALSE);
	return(TRUE);
}

int setdebug(typetask *taskptr)
{
	prompt (taskptr, "set debug => ");
	getnumber (taskptr, &debug);
}
	
int playwithalloc(typetask *taskptr)
{		     
	prompt(taskptr,"playwithalloc\n");
	lookatalloc();
}   

bool getretrieveendsets(typetask *taskptr, typespecset *specsetptr)
{
	return (getspecset (taskptr, specsetptr));
}

bool getxaccount(typetask *taskptr, typeisa *accountptr)
{
  bool validaccount();
/*tumblerclear (accountptr);
return (TRUE);
*/

       /* prompt (taskptr, "account? ");*/
	
	   gettumbler (taskptr, accountptr)
	&& validaccount(taskptr, accountptr);
	 taskptr->account = *accountptr;
	fprintf(stderr,"in get xaccount \n");
	return(TRUE);
}



int getcreatenode_or_account(typetask *taskptr, tumbler *tp)
{
  gettumbler(taskptr,tp);
	return(TRUE);
}

int getopen(typetask *taskptr, tumbler *tp, int *typep, int *modep)
{

gettumbler(taskptr,tp);
getnumber(taskptr,typep);
getnumber(taskptr,modep);
	return(TRUE);
}

int getclose(typetask *taskptr, tumbler *tp)
{
  gettumbler(taskptr,tp);
	return(TRUE);
}
