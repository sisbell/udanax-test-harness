/* Copyright � 1979-1999 Udanax.com. All rights reserved.

* This code is licensed under the terms of The Udanax Open-Source License, 
* which contains precisely the terms of the X11 License.  The full text of 
* The Udanax Open-Source License can be found in the distribution in the file 
* license.html.  If this file is absent, a copy can be found at 
* http://udanax.xanadu.com/license.html and http://www.udanax.com/license.html
*/
#include "xanadu.h"
#include "enf.h"
#include "players.h"

typedef struct {
	int connection;
	tumbler documentid;
	char created,modified;
	int type;
	int count;
}bertentry;

typedef struct conscell{
	struct conscell *next;
	bertentry *stuff;
}conscell;

int primes[] = {3,7,11,17,37,41,59,71,97,103,113,131,151,137,277,421,433,567,643,743};
#define NUMBEROFBERTTABLE 1327

static conscell *berttable[NUMBEROFBERTTABLE];

#ifndef DISTRIBUTION
char *bertModeNames[] = { "BADMODE", "ONLY", "COPYIF", "COPY" };
char *bertTypeNames[] = { "NOBERT", "READBERT", "WRITEBERT" };
char bertMsgBuf[256] = "";
#endif

/*  checkforopen
	Returns:  >0 for sufficiently open
			integer indicates type of open
		  0 if open required
		 -1 if new version should be made

	Open state -->
	type		    Not Open	#   Open READ	#  Open WRITE
	  |		!owned	| owned	#conn==	|conn!=	#conn==	|conn!=
	  v		--------+-------#-------+-------#-------+-------
	READ		   0	|   0	#  READ |   0   # WRITE | -1
	------------------------+-------#-------+-------#-------+-------
	WRITE		  -1	|   0	#  -1	|  -1	# WRITE | -1
	
*/
int checkforopen(tumbler *tp, int type, int connection)
{
  conscell *p;
  bertentry *bert;
  int foundnonread = FALSE;
  /* isthisusersdocument() prototype in protos.h */

  if (type == NOBERTREQUIRED) {
    return 1;	/* Random > 0 */
  }

  for (p = berttable[hashoftumbler(tp)]; p && p->stuff; p = p->next) {
    bert = p->stuff;
    if (tumblereq(tp, &bert->documentid)) {
      if (connection == bert->connection) {
	  switch (bert->type) {
	    case READBERT:
		return (type == READBERT) ? READBERT : /* WRITE */ -1;
	    case WRITEBERT:
		return WRITEBERT;
	  }
      } else {
          if (bert->type != READBERT) {
            foundnonread = TRUE;
          }
      }
    }
  }

  if (!foundnonread && (type == READBERT || isthisusersdocument(tp))) {
    return 0;
  } else {
    return -1;
  }

}



int logbertmodifiedforcrum(typecuc *crumptr, int connection)
{
	/*logbertmodified(xxx);*/
}


int logbertmodified(tumbler *tp, int connection)
{
  conscell *p;
  bertentry *bert;
/*fprintf(stderr,"logbertmodified user= %d  bert= ", connection);dumptumbler(tp);fprintf(stderr,"\n");*/
	for (p = berttable[hashoftumbler(tp)]; p && p->stuff; p = p->next) {
		bert =(bertentry *) p->stuff;
		if (bert->connection == connection && tumblereq(tp, &bert->documentid)) {
			bert->modified = TRUE;
			return(0);
		}
	}
}


int incrementopen(tumbler *tp, int connection)
{
  conscell *p;
  bertentry *bert;
#ifndef DISTRIBUTION
fprintf(stderr,"incrementopen:  user = %d  tp = ",connection);dumptumbler(tp);fprintf(stderr,"\n");
#endif
	for (p = berttable[hashoftumbler(tp)]; p && p->stuff; p = p->next) {
		bert = (bertentry *)p->stuff;
		if (bert->connection == connection && tumblereq(tp, &bert->documentid)) {
			bert->count += 1;
		}
	}
}


int addtoopen(tumbler *tp, int connection, int created, int type)
{
  int hash;
  conscell *consp;
  bertentry *ptr;
#ifndef DISTRIBUTION
fprintf(stderr,"addtoopen:  user = %d  type = %s  created = %d  tp = ", connection, bertTypeNames[type],created);dumptumbler(tp);fprintf(stderr,"\n");
#endif
	hash = hashoftumbler(tp);
	/* these eallocwithtags changed to malloc by hill zzzz*/
	if ((ptr = (bertentry *)eallocwithtag(sizeof(bertentry),BERTTAG)) == NULL)
		gerror("out of memory\n");
	tumblercopy(tp,&ptr->documentid);
	ptr->connection = connection;
	ptr->count = 1;
	ptr->created = created;
	ptr->modified = FALSE;
	ptr->type = type;
	if ((consp = (conscell *)eallocwithtag (sizeof(conscell),BERTCONSCELLTAG)) == NULL)
		gerror("out of memory\n");
	consp->stuff = ptr;
	consp->next = berttable[hash];
	berttable[hash] = consp;
}


bool removefromopen(tumbler *tp, int connection)
{
  int hash;
  conscell *p,*oldptr;
  conscell *temp;
  bertentry *bert;
  int status;
#ifndef DISTRIBUTION
fprintf(stderr,"removefromopen:  user = %d  tp = ", connection);dumptumbler(tp);fprintf(stderr,"\n");
#endif
	hash = hashoftumbler(tp);
	oldptr = NULL;
	for (p = berttable[hash]; p && p->stuff; p = p->next) {
		bert = p->stuff;
		if (bert->connection == connection && tumblereq(tp, &bert->documentid)) {
			if (--bert->count) {
				return TRUE;
			}
		/*	status = bert->modified && bert->created ; */
			status = bert->created && !bert->modified;
			if (status) {
				deleteversion(tp);
			}
			efree(p->stuff);
			if (oldptr == NULL) {
				temp = berttable[hash];
				berttable[hash] = berttable[hash]->next;
				efree((char *)temp);
				return TRUE;
			} else {
				temp = oldptr->next;
				oldptr->next = p->next;
				efree((char *)temp);
				return TRUE;
			}
		}
		oldptr = p;
	}
	return FALSE;
}

int exitbert(int connection)
{
  conscell *p,*oldptr;
  conscell *temp;
  bertentry *bert;
  int i;
  int status;
#ifndef DISTRIBUTION
fprintf(stderr,"exitbert:  user = %d\n", connection);
#endif
    oldptr = NULL;
    for (i = 0; i < NUMBEROFBERTTABLE;i++) {
	for (p = berttable[i]; p && p->stuff; p = p->next) {
		bert = p->stuff;
		if (bert->connection == connection) {
			status = bert->modified && bert->created ; 
			if (status) {
				deleteversion(&bert->documentid);
			}
			efree((char *)p->stuff);
			if (oldptr == NULL) {
				temp = berttable[i];
				berttable[i] = berttable[i]->next;
				efree((char *)temp);
				return(0);
			} else {
				temp = oldptr->next;
				oldptr->next = p->next;
				efree((char *)temp);
				return(0);
			}
		}
		oldptr = p;
	}
    }

}


int hashoftumbler(tumbler *tp)
{
  int ret;
  int i;

	ret = tp->exp;
	for (i = 0; i < NPLACES; i++) {
		ret += tp->mantissa[i] * primes[i];
	}
	return ret % NUMBEROFBERTTABLE;
}

/*
	Open state -->
	type & mode	     Not Open	#   Open READ	#   Open WRITE
	  |		!owned	| owned	#conn==	|conn!=	#conn==	|conn!=
	  v		========+=======#=======+=======#=======+=======
		read	   0	|   0   #   0   |   0   #  -1   |   -1
	COPYIF	----------------+-------#-------+-------#-------+-------
		write	  -1    |   0   #  -1   |  -1   #  -1   |   -1
		================+=======#=======+=======#=======+=======
		read	   0    |   0   #   0   |   0   #   X   |    X
	ONLY	----------------+-------#-------+-------#-------+-------
		write	   X    |   0   #   X   |   X   #   X   |    X
		================+=======#=======+=======#=======+=======
		read	  -1    |  -1   #  -1   |  -1   #  -1   |   -1
	COPY	----------------+-------#-------+-------#-------+-------
		write	  -1    |  -1   #  -1   |  -1   #  -1   |   -1

*/
bool doopen(typetask *taskptr, tumbler *tp, tumbler *newtp, int type, int mode, int connection)
{
  INT openState;
  bool docreatenewversion();

   if (type == NOBERTREQUIRED) {
	return 1;
   }

   if (mode == BERTMODECOPY) {
	docreatenewversion(taskptr, tp, &taskptr->account, newtp);
	addtoopen(newtp, connection, TRUE, type);
	return 1;
   }

   openState = checkforopen(tp, type, connection);

   if (openState == 0) {
	addtoopen(tp, connection, FALSE, type);
	tumblercopy(tp, newtp);
	return 1;
   }

   switch (mode) {
    case BERTMODECOPYIF:
	if (openState == -1) {
		docreatenewversion(taskptr, tp, &taskptr->account, newtp);
		addtoopen(newtp, connection, TRUE, type);
	} else if (type != WRITEBERT && openState != WRITEBERT) {
		incrementopen(tp, connection);
		tumblercopy(tp, newtp);
	} else {
		docreatenewversion(taskptr, tp, &taskptr->account, newtp);
		addtoopen(newtp, connection, TRUE, type);
	}
	return 1;
    case BERTMODEONLY:
	if (openState == -1 || type == WRITEBERT || openState == WRITEBERT) {
		return 0;
	} else {
		incrementopen(tp, connection);
		tumblercopy(tp, newtp);
		return 1;
	}
     default:
	gerror("DEFAULT CASE IN DOOPEN");
	return -999;
    }
}


bool doclose(typetask *taskptr, tumbler *tp, int connection)
{
#ifndef DISTRIBUTION
fprintf(stderr,"doclose: user = %d  tp = ",connection);dumptumbler(tp);fprintf(stderr,"\n");
#endif
	if (!removefromopen(tp, connection))
#ifndef DISTRIBUTION
		fprintf(stderr, "Bert was not open!\n")
#endif
		;
	return TRUE; /* for now, so as to not upset front-end */
}


int dobertexit(int connection)
{
#ifndef DISTRIBUTION
fprintf(stderr, "dobertexit: user = %d\n", connection);
#endif
	exitbert(connection);
}


int deleteversion(tumbler *tp)
{
#ifndef DISTRIBUTION
fprintf(stderr,"deleteversion: tp = ");dumptumbler(tp);fprintf(stderr,"\n");
#endif
}

