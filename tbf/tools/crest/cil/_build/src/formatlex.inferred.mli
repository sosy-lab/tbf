exception Eof
exception InternalError of string
module H :
  sig
    type ('a, 'b) t = ('a, 'b) Hashtbl.t
    val create : int -> ('a, 'b) t
    val clear : ('a, 'b) t -> unit
    val add : ('a, 'b) t -> 'a -> 'b -> unit
    val copy : ('a, 'b) t -> ('a, 'b) t
    val find : ('a, 'b) t -> 'a -> 'b
    val find_all : ('a, 'b) t -> 'a -> 'b list
    val mem : ('a, 'b) t -> 'a -> bool
    val remove : ('a, 'b) t -> 'a -> unit
    val replace : ('a, 'b) t -> 'a -> 'b -> unit
    val iter : ('a -> 'b -> unit) -> ('a, 'b) t -> unit
    val fold : ('a -> 'b -> 'c -> 'c) -> ('a, 'b) t -> 'c -> 'c
    val length : ('a, 'b) t -> int
    module type HashedType =
      sig type t val equal : t -> t -> bool val hash : t -> int end
    module type S =
      sig
        type key
        type 'a t
        val create : int -> 'a t
        val clear : 'a t -> unit
        val copy : 'a t -> 'a t
        val add : 'a t -> key -> 'a -> unit
        val remove : 'a t -> key -> unit
        val find : 'a t -> key -> 'a
        val find_all : 'a t -> key -> 'a list
        val replace : 'a t -> key -> 'a -> unit
        val mem : 'a t -> key -> bool
        val iter : (key -> 'a -> unit) -> 'a t -> unit
        val fold : (key -> 'a -> 'b -> 'b) -> 'a t -> 'b -> 'b
        val length : 'a t -> int
      end
    module Make :
      functor (H : HashedType) ->
        sig
          type key = H.t
          type 'a t = 'a Hashtbl.Make(H).t
          val create : int -> 'a t
          val clear : 'a t -> unit
          val copy : 'a t -> 'a t
          val add : 'a t -> key -> 'a -> unit
          val remove : 'a t -> key -> unit
          val find : 'a t -> key -> 'a
          val find_all : 'a t -> key -> 'a list
          val replace : 'a t -> key -> 'a -> unit
          val mem : 'a t -> key -> bool
          val iter : (key -> 'a -> unit) -> 'a t -> unit
          val fold : (key -> 'a -> 'b -> 'b) -> 'a t -> 'b -> 'b
          val length : 'a t -> int
        end
    val hash : 'a -> int
    external hash_param : int -> int -> 'a -> int = "caml_hash_univ_param"
      "noalloc"
  end
module E :
  sig
    val logChannel : out_channel ref
    val debugFlag : bool ref
    val verboseFlag : bool ref
    val colorFlag : bool ref
    val redEscStr : string
    val greenEscStr : string
    val yellowEscStr : string
    val blueEscStr : string
    val purpleEscStr : string
    val cyanEscStr : string
    val whiteEscStr : string
    val resetEscStr : string
    val warnFlag : bool ref
    exception Error
    val error : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val bug : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val unimp : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val s : 'a -> 'b
    val hadErrors : bool ref
    val warn : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val warnOpt : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val log : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val logg : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val null : ('a, unit, Pretty.doc, unit) format4 -> 'a
    val pushContext : (unit -> Pretty.doc) -> unit
    val popContext : unit -> unit
    val showContext : unit -> unit
    val withContext : (unit -> Pretty.doc) -> ('a -> 'b) -> 'a -> 'b
    val newline : unit -> unit
    val newHline : unit -> unit
    val getPosition : unit -> int * string * int
    val getHPosition : unit -> int * string
    val setHLine : int -> unit
    val setHFile : string -> unit
    val setCurrentLine : int -> unit
    val setCurrentFile : string -> unit
    type location =
      Errormsg.location = {
      file : string;
      line : int;
      hfile : string;
      hline : int;
    }
    val d_loc : unit -> location -> Pretty.doc
    val d_hloc : unit -> location -> Pretty.doc
    val getLocation : unit -> location
    val parse_error : string -> 'a
    val locUnknown : location
    val readingFromStdin : bool ref
    val startParsing : ?useBasename:bool -> string -> Lexing.lexbuf
    val startParsingFromString :
      ?file:string -> ?line:int -> string -> Lexing.lexbuf
    val finishParsing : unit -> unit
  end
val keywords : (string, Formatparse.token) H.t
val scan_ident : string -> Formatparse.token
val init : prog:string -> Lexing.lexbuf
val finish : unit -> unit
val error : string -> 'a
val scan_escape : string -> string
val get_value : char -> int
val scan_hex_escape : string -> string
val scan_oct_escape : string -> string
val wbtowc : string -> string
val wstr_to_warray : string -> string
val getArgName : Lexing.lexbuf -> int -> string
val __ocaml_lex_tables : Lexing.lex_tables
val initial : Lexing.lexbuf -> Formatparse.token
val __ocaml_lex_initial_rec : Lexing.lexbuf -> int -> Formatparse.token
val comment : Lexing.lexbuf -> unit
val __ocaml_lex_comment_rec : Lexing.lexbuf -> int -> unit
val endline : Lexing.lexbuf -> Formatparse.token
val __ocaml_lex_endline_rec : Lexing.lexbuf -> int -> Formatparse.token
