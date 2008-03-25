# Copyright 2005-2008 Nanorex, Inc.  See LICENSE file for details. 
"""
preferences.py -- Preferences system.

@author: bruce
@version: $Id: preferences.py 11951 2008-03-14 04:44:50Z ericmessick $
@copyright: 2005-2008 Nanorex, Inc.  See LICENSE file for details.

Module classification: [bruce 071215]

At least foundation, due to integral use of "from changes import UsageTracker".
But also could be construed to have lots of app-specific knowledge,
due to "from prefs_constants import prefs_table". But for now, experiment
with pretending that's not app-specific, which we can get away with since
it's pure data... and this might even make sense, if different apps
share code which references the same prefs_keys from that table,
as long as we make sure they can use different (per-app) prefs files.
(For the same reason, we'll also classify prefs_constants as foundation
or lower. In fact, it'll be utilities or constants for now, as explained
in its docstring.)

A desirable refactoring might be to classify prefs_constants higher
(model or a specific app) and pass it to a prefs singleton as an argument.
Then it'd be more clearly ok to call this module "foundation", but let
prefs_constants be higher. OTOH, the reason explained above may make it
perfectly ok for prefs_constants to be very low.

==

Prototype for Alpha.

See lower-down docstrings for usage.

==

History:

bruce 050106 or so: created it.

[some minor changes since then]

bruce 050804: added prefs usage/change tracking.

==

Should be used with bsddb,
but works without it too, after printing a warning.
The module bsddb is present in our standard installations
of windows and linux python, but not yet Mac python;
but we can add it, since it's easily available from

  http://undefined.org/python/pimp/darwin-7.0.0-Power_Macintosh.html

(package bsddb3 4.1.6)

BUT WE SHOULD LOOK INTO THE LICENSE TO MAKE SURE IT'S OK!
(It probably is, and [050804] I think Huaicai investigated this
 and confirmed that it is.)
"""

import os
import time
import sys

#from utilities import debug_flags

#try:
#    atom_debug # don't disturb it if already set (e.g. by .atom-debug-rc)
#except:
#    try:
#        atom_debug = os.environ['ATOM_DEBUG'] # as a string; should be "1" or "0"
#    except:
#        atom_debug = 0
#    try:
#        atom_debug = int(atom_debug)
#    except:
#        pass
#    atom_debug = not not atom_debug

#if atom_debug:
#    print "fyi: user has requested ATOM_DEBUG feature; extra debugging code enabled; might be slower"

# ==

# debug flags for dna updater, controlled by debug_prefs
# in dna_updater.dna_updater_prefs.
# The default values set here don't matter, afaik,
# since they are replaced by debug_pref values before use.
# [bruce 080228 moved these here]

DEBUG_DNA_UPDATER_MINIMAL = True

DEBUG_DNA_UPDATER = True

DEBUG_DNA_UPDATER_VERBOSE = False

DNA_UPDATER_SLOW_ASSERTS = True


def mkdirs_in_filename(filename):
    """
    Make all directories needed for the directory part of this filename,
    if nothing exists there. Never make the filename itself (even if it's
    intended to be a directory, which we have no way of knowing anyway).
    If something other than a directory exists at one of the dirs we might
    otherwise make, we don't change it, which will probably lead to errors
    in this function or in the caller, which is fine.
    """
    dir, file = os.path.split(filename)
    if not os.path.exists(dir):
        mkdirs_in_filename(dir)
        os.mkdir(dir)
    return

# Finding or making special directories and files (e.g. in user's homedir):

# code which contains hardcoded filenames in the user's homedir, etc
# (moved into this module from MWsemantics.py by bruce 050104,
#  since not specific to one window, might be needed before main window init,
#  and the directory names might become platform-specific.)

_tmpFilePath = None

def find_or_make_Nanorex_directory():
    """
    Find or make the directory ~/Nanorex, in which we will store
    important subdirectories such as Preferences, temporary files, etc.
    If it doesn't exist and can't be made, try using /tmp.
    [#e Future: for Windows that backup dir should be something other than /tmp.
     And for all OSes, we should use a more conventional place to store prefs
     if there is one (certainly there is on Mac).]
    """
    global _tmpFilePath
    if _tmpFilePath:
        return _tmpFilePath # already chosen, always return the same one
    _tmpFilePath = _find_or_make_nanorex_dir_0()
    assert _tmpFilePath
    return _tmpFilePath

def _find_or_make_nanorex_dir_0():
    """
    private helper function for find_or_make_Nanorex_directory
    """
    #Create the temporary file directory if not exist [by huaicai ~041201]
    # bruce 041202 comments about future changes to this code:
    # - we'll probably rename this, sometime before Alpha goes out,
    #   since its purpose will become more user-visible and general.
    # - it might be good to create a README file in the directory
    #   when we create it. And maybe to tell the user we created it,
    #   in a dialog.
    # - If creating it fails, we might want to create it in /tmp
    #   (or wherever some python function says is a good temp dir)
    #   rather than leaving an ususable path in tmpFilePath. This
    #   could affect someone giving a demo on a strange machine!
    # - If it exists already, we might want to test that it's a
    #   directory and is writable. If we someday routinely create
    #   a new file in it for each session, that will be a good-
    #   enough test.
    tmpFilePath = os.path.normpath(os.path.expanduser("~/Nanorex/"))
    if not os.path.exists(tmpFilePath):
        try:
            os.mkdir(tmpFilePath)
        except:
            sys.exit
            #bruce 041202 fixed minor bug in next line; removed return statement
            #print_compact_traceback("exception in creating temporary directory: \"%s\"" % tmpFilePath)
            #bruce 050104 new feature [needs to be made portable so it works on Windows ###@@@]
            os_tempdir = "/tmp"
            print "warning: using \"%s\" for temporary directory, since \"%s\" didn't work" % (os_tempdir, tmpFilePath)
            tmpFilePath = os_tempdir
    #e now we should create or update a README file in there [bruce 050104]
    return tmpFilePath

#import foundation.env as env
#import utilities.EndUser as EndUser
#from utilities.debug import print_compact_traceback

#from foundation.changes import UsageTracker

#from prefs_constants import prefs_table

# some imports remain lower down, for now: bsddb and shelve


"""
Some internal & client-code documentation, as of 050106:

We store prefs in a shelf. Restrictions imposed by the shelve module:
Keys must be strings, values can be any pickleable python exprs,
and neither can be extremely long (exact limits are not made clear).

When these restrictions become a problem, we will make our intermediating
layer handle them (for example, by translating long keys to short ones).

==

Concurrent access:

We usually keep the shelf closed, in case other processes want to access or modify it too.
This only works if we assume that these processes only open it briefly when processing
some user event (typed command or clicked button), and this doesn't happen in two processes
at once since the user can only give events to one process at a time. For this reason,
it's important to only open it briefly during a user event (and only at the beginning
if the processing takes a long time), and never any other time!

Also, if you (a process) start another process which might access the prefs when it starts,
you should only access them yourself just before it starts (and during subsequent user events,
assuming that subprocess follows the same rule).

We rely on the client code to follow these rules; we don't try to enforce them.
Breaking them might conceivably trash the entire prefs database, or perhaps more likely,
cause an error in the process trying to access it while another process is doing so.
(This depends on the db module, and I don't know what bsddb does in this case.)

We make no attempt yet to handle these errors or back up the prefs database.

==

Internal shelf key usage:

Current internal shelf key usage (this might change at any time,
without the client-code keys changing):

Keys starting "k " are translated versions of client-code keys;
see internal _attr2key method (which will be renamed).

Keys starting '_' or with a digit are reserved for use by this code.
In fact, all other keys are reserved. Presently used: see the code.
The most important one is _format_version.

==

High-level keys and values:

Keys supplied by client code (translated through _attr2key into shelf keys)
are presently just strings, using conventions still mostly to be invented,
but in the future will be able to be more kinds of objects.

Values supplied by client code will in the future be translated, and have
metainfo added, but this is not yet done. Values must be pickleable, and
also should not include instances of classes until we decide which of
those are ok. (But Numeric arrays are ok.)

For now, all modules use the same global namespace of high-level keys,
but this might change. To permit this, the module defining the key
needs to be detectable by this code... basically this means any given key
should be passed into this module from the same external module.
Details to be documented when they are implemented and become relevant.

==

Usage by client code (for now -- this might change!):

  from foundation.preferences import prefs_context
  
  prefs = prefs_context()
  
  key = "some string" # naming conventions to be introduced later
  
  prefs[key] = value
  
  value = prefs[key] # raises KeyError if not there
  
  # these dict-like operations might or might not work
  # (not yet tested; someday we will probably suppport them
  # and make them more efficient than individual operations
  # when several prefs are changed at once)
  
  prefs.get(key, defaultvalue)
  
  prefs.update(dict1)
  
  dict1.update(prefs)

"""

# ===

# This module wants bsddb, just to make sure the shelf is stored in a format
# that (we hope) all platforms can open. (It also might be more reliable,
# be better at concurrent access, and/or permit longer keys and (especially)
# values than other db packages.)

# But, we'll run without it if necessary, but when we do, we'll use a different
# shelf name, in case the binary formats are incompatible. (Not a perfect solution,
# since there's no guarantee the db format without bsddb is always the same...
# but I don't know a good-enough way to find out which db module shelve is actually using.)

try:
    import bsddb3 as _junk
    _junk # try to tell pylint we need this import [bruce 071023]
except:
    sys.exit(1)
else:
    dbname = "bsddb"

# And this module requires shelve. We assume without checking that if bsddb is available,
# shelve will use it. (I don't know any straightforward way to check this. But the
# docs for shelve say it will use it, I think. #k check this ###@@@)

from bsddb3 import dbshelve

# (For the actual filename of the prefs file, see the code of _make_prefs_shelf()
#  below, which specifies the basename only; the db module decides what extension
#  to add. This is one reason we store the prefs in a subdirectory.)

# ===

_shelfname = _shelf = _cache = None

_defaults = _trackers = None #bruce 050804 new features

def _make_prefs_shelf():
    """[private function]
    call this once per session,
    to create or find the shelf (whose name depends only on the dbm format we'll use for it),
    and create the cache of its contents,
    and store a comment there about this process,
    and close the shelf again in case a concurrent process is sharing the same shelf with us.
    """
    global _shelfname, _shelf, _cache, _defaults, _trackers
    nanorex = find_or_make_Nanorex_directory()
    global dbname
    _shelfname = os.path.join( nanorex, "Preferences", "%s-shelf" % dbname )
        # This name should differ when db format differs.
        # Note: the actual filename used might have an extension added
        # by the db module (in theory, it might even create two files
        # with different extentions from the given basename).
        # By experiment, on the Mac, with bsddb there is no extension added,
        # and without it there is '.db' added. [bruce 050105]
    mkdirs_in_filename(_shelfname)
    _shelf = dbshelve.open(_shelfname)
    _cache = {}
    _cache.update(_shelf) # will this work?
    _defaults = {}
    _trackers = {}
    # zap obsolete contents
    obskeys = []
    for key in _cache.keys():
        if key.isdigit() or key in ['_session_counter']:
            obskeys.append(key)
    for key in obskeys:
        del _shelf[key]
        del _cache[key]
    ###@@@ following should be revised to handle junk contents gracefully,
    # and to notice the existing format version and handle older formats appropriately
    # or reject them gracefully.
    _store_while_open('_format_version', 'preferences.py/v050106')
        # storing this blindly is only ok since the only prior version is one
        # we can transparently convert to this one by the "zap obskeys" above.
    
    # store a comment about the last process to start using this shelf
    # (nothing yet looks at this comment)
    proc_info = "process: pid = %d, starttime = %r" % (os.getpid(), time.asctime())
    _store_while_open( '_fyi/last_proc', proc_info ) # (nothing yet looks at this)
    _close()
    return

def _close():
    global _shelf
    _shelf.close()
    _shelf = None
    return

def _reopen():
    _ensure_shelf_exists()
    global _shelf
    assert _shelf is None
    _shelf = dbshelve.open(_shelfname)
    # don't bother to re-update our _cache! This would be too slow to do every time.
    return

def _store_new_while_open(key, val): # [not used as of 050804]
    assert not _shelf.has_key(key) # checks _shelf, not merely _cache
    assert not _cache.has_key(key)
    _cache[key] = val
    _shelf[key] = val
    return

def _store_while_open(key, val): # [used only when initializing the shelf, as of 050804]
    # don't assert _cache and _shelf are the same at this key -- it's not an error if they are not,
    # or if shelf has a value and cache does not, since a concurrent process is allowed to write
    # a prefs value on its own.
    _cache[key] = val
    _shelf[key] = val
    return

def _ensure_shelf_exists():
    if not _shelfname:
        _make_prefs_shelf()
    return

#bruce 050804/050805 new features:

def _track_change(pkey): 
    _tracker_for_pkey( pkey).track_change()
    
def _track_use(pkey):
    _tracker_for_pkey( pkey).track_use()
    
def _tracker_for_pkey(pkey):
    try:
        return _trackers[pkey]
    except KeyError:
        sys.exit(1)
        #tracker = _trackers[pkey] = UsageTracker()
        #return tracker
    pass

def _get_pkey_key(pkey, key): #bruce 050804 split this out of __getitem__ so I can also use it in get (both methods)
    "[#doc better; note: pkey and key args are redundant; they're both provided just for this implem's convenience]"
    _track_use(pkey) # note, this is done even if we raise KeyError below (which is good)
    try:
        return _cache[pkey]
    except KeyError:
        raise KeyError, key # note: exception detail is key, not pkey as it would be if we just said "raise"
    pass

def _get_pkey_faster(pkey): # optimization of _get_pkey_key(pkey, key) when the KeyError exception detail doesn't matter
    _track_use(pkey)
    return _cache[pkey]

def _record_default( pkey, dflt):
    """Record this default value (if none is yet known for pkey),
    so other code can find out what the default value is,
    for use in "restore defaults" buttons in prefs UI.
    In debug version, also ensure this is the same as any previously recorded default value.
       Note, dflt can be anything, even None, though some callers have a special case
    which avoids calling this when dflt is None.
    """
    _defaults.setdefault( pkey, dflt) # only affects it the first time, for a given pkey
    if debug_flags.atom_debug:
        # also check consistency each time
        if dflt != _defaults[pkey]:
            print "atom_debug: bug: ignoring inconsistent default %r for pref %r; retaining %r" % \
                  ( dflt, pkey, _defaults[pkey] ) #e also print key if in future the key/pkey relation gets more complex
    return

def _restore_default_while_open( pkey): #bruce 050805
    """Remove the pref for pkey from the prefs db (but no error if it's not present there).
    As for the internal value of the pref (in _cache, and for track_change, and for subscriptions to its value):
    If a default value has been recorded, change the cached value to that value
    (as it would be if this pref had originally been missing from the db, and a default value was then recorded).
    If not, remove it from _cache as well, and use the internal value of None.
    Either way, if the new internal value differs from the one before this function was called,
    track the change and fulfill any subscriptions to it.
       If possible, don't track a use of the prefs value.
    """
    priorval = _cache.get(pkey) # might be None
    if _shelf.has_key(pkey):
        del _shelf[pkey]
    try:
        dflt = _defaults[pkey]
    except KeyError:
        if debug_flags.atom_debug:
            print "atom_debug: fyi: restore defaults finds no default yet recorded for %r; using None" % pkey
        _cache[pkey] = dflt = None
        del _cache[pkey]
    else:
        _cache[pkey] = dflt
    if dflt != priorval:
        _track_change(pkey)
        #e fulfill any subscriptions to this value (if this is ever done by something other than track_change itself)
    return

def keys_list( keys): #bruce 050805
    """Given a key or a list of keys (or a nested list), return an equivalent list of keys.
    Note: tuples of keys are not allowed (someday they might be a new kind of primitive key).
    """
    res = []
    if type(keys) == type([]):
        for sub in keys:
            res.extend( keys_list( sub) )
                #e could be optimized (trivially, if we disallowed nested lists)
    else:
        assert type(keys) == type("a")
        res.append(keys)
    return res

# ==

# Now make a prefs function, which returns a prefs object [someday] customized for the calling module,
# in which prefs can be accessed or stored using attributes, whose names are interpreted in a context
# which might differ for each module.

_NOT_PASSED = [] # private object for use as keyword arg default [bruce 070110, part of fixing bug of None as Choice value]
    # (note, the same global name is used for different objects in preferences.py and debug_prefs.py)

class _prefs_context:
    """Represents a symbol context for prefs names, possibly [someday] customized for one module.
    """
    def __init__(self, modname):
        # modname is not presently used
        _ensure_shelf_exists() # needed before __getattr__ and __getitem__ are called
        self.trackers = {}
    def _attr2key(self, attr):
        return "k " + attr # stub! (i guess)
    #e Someday we will support more complex keys,
    # which are like exprs whose heads (at all levels) are in our context.
    # For now, just support arbitrary strings as items.
    def __setitem__(self, key, val):
        assert type(key) == type("a") # not unicode, numbers, lists, ... for now
        pkey = self._attr2key(key) # but we might use a more general func for this, at some point
        try:
            #bruce 050804 new feature: detect "change with no effect" (where new value equals existing value),
            # so we can avoid tracking that as an actual change.
            # We also avoid tracking this as a use (even though we do use the value for the comparison).
            # And, while we're at it, optimize by not changing the prefs db in this case.
            # This is not just an optimization, since if the prefs db contains no value for this pref,
            # and no value other than the default value (according to the current code) has been stored during this session
            # and if this remains true in the present call (i.e. val equals the default value),
            # then (due to some of today's changes to other code here, particularly self.get storing dflt in cache), #####IMPLEM
            # we won't store anything in the prefs db now.            
            cached_val = _cache[pkey] # this might be a default value from the present code which is not in the prefs db
        except KeyError:
            same = False
        else:
            # If no default value is known, we consider any value to differ from it.
            # [##e Would it be better to treat this as if the default value was None (like prefs.get does)??]
            same = (val == cached_val)
        if same:
            if 0 and debug_flags.atom_debug:
                print "atom_debug: fyi: returning early from prefs.__setitem__(%r) since val == cached_val, %r == %r" % (key, val, cached_val)
            return # see long comment above
        if _shelf:
            _shelf[pkey] = _cache[pkey] = val
            #Next line removed because I don't care about tracking changes right now. (Derrick)
#            _track_change(pkey) # do this only after the change happens, for the sake of formulas...
                #e (someday we might pass an arg saying the change is done, or the curval is merely invalid,
                #   and if the latter, whether another track_change will occur when the change is done.)
        else:
            try:
                _reopen()
                _shelf[pkey] = _cache[pkey] = val
                _track_change(pkey)
            finally:
                _close()
        return
    def __getitem__(self, key):
        assert type(key) == type("a")
        pkey = self._attr2key(key)
        return _get_pkey_key( pkey, key)
    def get(self, key, dflt = _NOT_PASSED): #bruce 050117; revised 050804, and 070110 to use _NOT_PASSED
        assert type(key) == type("a")
        pkey = self._attr2key(key)
        if dflt is not _NOT_PASSED:
            _record_default( pkey, dflt)
            #bruce 070110 bugfix: use _NOT_PASSED rather than None.
            # Before this fix, passing None explicitly as dflt would fail to record it, which could cause later exceptions
            # when client code used env.prefs[key] if the pref had never been saved. This was one of two bugs in
            # using a Choice value of None in debug_prefs.py. The other part is fixed in debug_prefs.py dated today.
        del dflt # [if dflt was used below and we removed this del, we'd need to replace _NOT_PASSED with None in this localvar]
        try:
            return _get_pkey_faster( pkey) # optim of self[key]
                # note: usage of this pref is tracked in _get_pkey_faster even if it then raises KeyError.
        except KeyError:
            #bruce 050804 new features (see long comment in __setitem__ for partial explanation):
            # if default value must be used, then
            # (1) let it be the first one recorded regardless of the one passed to this call, for consistency;
            # (2) store it in _cache (so this isn't called again, and for other reasons mentioned in __setitem__)
            # but not in the prefs db itself.
            try:
                dflt = _defaults[pkey] # might be None, if that was explicitly recorded by a direct call to _record_default
            except KeyError:
                # no default value was yet recorded
                dflt = None # but don't save None in _cache in this case
                if debug_flags.atom_debug:
                    print "atom_debug: warning: prefs.get(%r) returning None since no default value was yet recorded" % (key,)
            else:
                _cache[pkey] = dflt # store in cache but not in prefs-db
            return dflt
        pass
    def update(self, dict1): #bruce 050117
        # note: unlike repeated setitem, this only opens and closes once.
        if _shelf:
            for key, val in dict1.items():
                #e (on one KeyError, should we store the rest?)
                #e (better, should we check all keys before storing anything?)
                self[key] = val #e could optimize, but at least this leaves it open
                    # that will do _track_use(pkey); if we optimize this, remember to do that here.
        else:
            try:
                _reopen()
                self.update(dict1)
            finally:
                _close()
        return
    def suspend_saving_changes(self): #bruce 051205 new feature
        """Let prefs changes after this point be saved in RAM and take full effect
        (including notifying subscribers),
        but not be saved to disk until the next call to resume_saving_changes
        (which should be called within the same user command or mouse drag,
        but not for every mouse motion during a drag).
        Use this to prevent constant updates to disk for every mouse motion
        during a drag (e.g. as a prefs slider is adjusted).
           Warn if called when changes are already suspended,
        but as a special case to mitigate bugs of failing to call resume,
        save all accumulated changes whenever called.
        """
        if _shelf:
            # already suspended -- briefly resume (so they're saved) before suspending (again)
            print "bug: suspend_saving_changes when already suspended -- probably means resume was missing; saving them now"
            _close()
        _reopen()
        return
    def resume_saving_changes(self, redundant_is_ok = False): #bruce 051205 new feature
        """Resume saving changes, after a call of suspend_saving_changes.
        Optional redundant_is_ok = True prevents a warning about a redundant call;
        this is useful for letting callers make sure changes are being saved
        when they should be (and probably already are).
        """
        if _shelf:
            if redundant_is_ok: # this case untested (no immediate use is planned as of 051205)
                print "Warning: resume_saving_changes(redundant_is_ok = True) was in fact redundant --"
                print " i.e. it may have been necessary to work around a bug and save prefs."
            _close()
        else:
            if not redundant_is_ok:
                print "warning: redundant resume_saving_changes ignored"
        return
    def restore_defaults(self, keys): #bruce 050805
        """Given a key or a list of keys,
        restore the default value of each given preference
        (if one has yet been recorded, e.g. if prefs.get has been provided with one),
        with all side effects as if the user set it to that value,
        but actually remove the value from the prefs db as well
        (so if future code has a different default value for the same pref,
         that newer value will be used by that future code).
        [#e we might decide to make that prefs-db-removal feature optional.]
        """
        if _shelf:
            for key in keys_list( keys):
                pkey = self._attr2key(key)
                _restore_default_while_open( pkey)
        else:
            try:
                _reopen()
                self.restore_defaults( keys)
            finally:
                _close()
        return
    
    def get_default_values(self, keys): #bruce 080131 UNTESTED @@@@
        """
        @param keys: a list of key strings (tuple not allowed; nested list not allowed)
        """
        assert type(keys) == type([])
        return map( self.get_default_value, keys)

    def get_default_value(self, key, _default_return_value = None): #bruce 080131/080201 UNTESTED @@@@
        """
        @param key: a key string
        """
        # review: should default value of _default_return_value be None (as now), or _NOT_PASSED?
        assert type(key) == type("")
        pkey = self._attr2key(key)
        dflt = _defaults.get(pkey, _default_return_value)
        return dflt
        
    def has_default_value(self, key): #bruce 080131/080201 UNTESTED @@@@
        """
        @param key: a key string
        """
        # This is a ###STUB in a few ways:
        # - it ought to compare using same_vals, not != (also in setitem??)
        # - the specification doesn't say what to do when no default is yet recorded
        # - old version without _NOT_PASSED:
        #   it might record a default of None if no default is yet recorded (not sure)
        # - new version with _NOT_PASSED: correctness not fully reviewed
        dflt = self.get_default_value(key, _NOT_PASSED)
        current = self.get(key, dflt) # does usage tracking (good)
        same = not (dflt != current)
            # (note: this is a safer comparison than ==, but not perfect,
            #  re Numeric arrays)
        return same

    def have_default_values(self, keys): #bruce 080201 UNTESTED @@@@
        """
        Return True if every prefs key in the given list currently has
        its default value (i.e. if restore_defaults would not
        change their current values).
        
        @param keys: a list of key strings (tuple not allowed; nested list not allowed)
        """
        assert type(keys) == type([])
        # note: I think this does not access the shelf,
        # so we don't need to optimize it to only open the shelf once.
        for key in keys:
            if not self.has_default_value(key):
                return False
        return True
    
    pass # end of class _prefs_context

# for now, in this stub code, all modules use one context:
_global_context = _prefs_context("allmodules")

def prefs_context():
    ###@@@ stub: always use the same context, not customized to the calling module.
    return _global_context

# ==

# initialization code [bruce 050805] (includes the set of env.prefs)

def declare_pref( attrname, typecode, prefskey, dflt = None ): # arg format is same as prefs_table record format
    assert typecode in ['color','boolean','string','int', 'float'] or type(typecode) == type([]) #e or others as we define them
    #e create type object from typecode
    #e get dflt from type object if it's None here, otherwise tell this dflt to type object
    #e record type object
    #e use attrname to set up faster/cleaner access to this pref?
    #e etc.

    # Record the default value now, before any other code can define it or ask for the pref.
    # (This value is used if that pref is not yet in the db;
    #  it's also used by "reset to default values" buttons in the UI,
    #  though those will have the side effect of defining that value in the db.)
    prefs = prefs_context()
    if dflt is not None:
        curvaljunk = prefs.get( prefskey, dflt)
    return

#def init_prefs_table( prefs_table): # sets env.prefs
#    for prefrec in prefs_table:
#        try:
#            declare_pref(*prefrec)
#        except:
#            sys.exit(1)
#           #print_compact_traceback( "ignoring prefs_table entry %r with this exception: " % (prefrec,) )
#        pass
    
#    env.prefs = prefs_context() # this is only ok because all modules use the same prefs context.
    
#    if 0 and debug_flags.atom_debug:
#        print "atom_debug: done with prefs_table" # remove when works
#    return

#init_prefs_table( prefs_table)
    # this is guaranteed to be done before any prefs_context object exists, including env.prefs
    # (but not necessarily just after this module is imported, though presently, it is;
    #  similarly, it's not guaranteed that env.prefs exists arbitrarily early,
    #  though in practice it does after this module is imported, and for now it's ok
    #  to write code which would fail if that changed, since it'll be easy to fix that code
    #  (and to detect that we need to) if it ever does change.)

# ==

'''
use prefs_context() like this:

prefs = prefs_context() # once per module which uses it (must then use it in the same module)

... prefs['atom_debug'] = 1

... if prefs['atom_debug']:
        ...

or make up keys as strings and use indexing, prefs[key],
but try to compute the strings in only one place
and use them from only one module.

We will gradually introduce naming conventions into the keys,
for example, module/subname, type:name. These will be documented
once they are formalized.

[these rules might be revised!]
'''

# == test code (very incomplete) [revised 050804 since it was out of date]

if __name__ == '__main__':
##    defaults = dict(hi = 2, lo = 1)
##    print "grabbing %r, got %r" % (defaults, grab_some_prefs_from_cache(defaults))
##    new = dict(hi = time.asctime())
##    print "now will store new values %r" % new
##    store_some_prefs(new)
##    print "now we grab in same way %r" % grab_some_prefs_from_cache(defaults) # this failed to get new value, but next proc gets it
##    print "done with this grossly incomplete test; the shelfname was", _shelfname

    # now try this:
    testprefs = prefs_context()
    testprefs['x'] = 7
    print "should be 7:",testprefs['x']
    
# end