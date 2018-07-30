module R :
  sig
    type regexp = Str.regexp
    val regexp : string -> regexp
    val regexp_case_fold : string -> regexp
    val quote : string -> string
    val regexp_string : string -> regexp
    val regexp_string_case_fold : string -> regexp
    val string_match : regexp -> string -> int -> bool
    val search_forward : regexp -> string -> int -> int
    val search_backward : regexp -> string -> int -> int
    val string_partial_match : regexp -> string -> int -> bool
    val matched_string : string -> string
    val match_beginning : unit -> int
    val match_end : unit -> int
    val matched_group : int -> string -> string
    val group_beginning : int -> int
    val group_end : int -> int
    val global_replace : regexp -> string -> string -> string
    val replace_first : regexp -> string -> string -> string
    val global_substitute : regexp -> (string -> string) -> string -> string
    val substitute_first : regexp -> (string -> string) -> string -> string
    val replace_matched : string -> string -> string
    val split : regexp -> string -> string list
    val bounded_split : regexp -> string -> int -> string list
    val split_delim : regexp -> string -> string list
    val bounded_split_delim : regexp -> string -> int -> string list
    type split_result = Str.split_result = Text of string | Delim of string
    val full_split : regexp -> string -> split_result list
    val bounded_full_split : regexp -> string -> int -> split_result list
    val string_before : string -> int -> string
    val string_after : string -> int -> string
    val first_chars : string -> int -> string
    val last_chars : string -> int -> string
  end
module L :
  sig
    val length : 'a list -> int
    val hd : 'a list -> 'a
    val tl : 'a list -> 'a list
    val nth : 'a list -> int -> 'a
    val rev : 'a list -> 'a list
    val append : 'a list -> 'a list -> 'a list
    val rev_append : 'a list -> 'a list -> 'a list
    val concat : 'a list list -> 'a list
    val flatten : 'a list list -> 'a list
    val iter : ('a -> unit) -> 'a list -> unit
    val map : ('a -> 'b) -> 'a list -> 'b list
    val rev_map : ('a -> 'b) -> 'a list -> 'b list
    val fold_left : ('a -> 'b -> 'a) -> 'a -> 'b list -> 'a
    val fold_right : ('a -> 'b -> 'b) -> 'a list -> 'b -> 'b
    val iter2 : ('a -> 'b -> unit) -> 'a list -> 'b list -> unit
    val map2 : ('a -> 'b -> 'c) -> 'a list -> 'b list -> 'c list
    val rev_map2 : ('a -> 'b -> 'c) -> 'a list -> 'b list -> 'c list
    val fold_left2 : ('a -> 'b -> 'c -> 'a) -> 'a -> 'b list -> 'c list -> 'a
    val fold_right2 :
      ('a -> 'b -> 'c -> 'c) -> 'a list -> 'b list -> 'c -> 'c
    val for_all : ('a -> bool) -> 'a list -> bool
    val exists : ('a -> bool) -> 'a list -> bool
    val for_all2 : ('a -> 'b -> bool) -> 'a list -> 'b list -> bool
    val exists2 : ('a -> 'b -> bool) -> 'a list -> 'b list -> bool
    val mem : 'a -> 'a list -> bool
    val memq : 'a -> 'a list -> bool
    val find : ('a -> bool) -> 'a list -> 'a
    val filter : ('a -> bool) -> 'a list -> 'a list
    val find_all : ('a -> bool) -> 'a list -> 'a list
    val partition : ('a -> bool) -> 'a list -> 'a list * 'a list
    val assoc : 'a -> ('a * 'b) list -> 'b
    val assq : 'a -> ('a * 'b) list -> 'b
    val mem_assoc : 'a -> ('a * 'b) list -> bool
    val mem_assq : 'a -> ('a * 'b) list -> bool
    val remove_assoc : 'a -> ('a * 'b) list -> ('a * 'b) list
    val remove_assq : 'a -> ('a * 'b) list -> ('a * 'b) list
    val split : ('a * 'b) list -> 'a list * 'b list
    val combine : 'a list -> 'b list -> ('a * 'b) list
    val sort : ('a -> 'a -> int) -> 'a list -> 'a list
    val stable_sort : ('a -> 'a -> int) -> 'a list -> 'a list
    val fast_sort : ('a -> 'a -> int) -> 'a list -> 'a list
    val merge : ('a -> 'a -> int) -> 'a list -> 'a list -> 'a list
  end
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
val preparse : string -> (string, string list) H.t
val errorWrap : string -> (string -> 'a) -> 'a
val getNthString : int -> ('a, 'b list) H.t -> 'a -> 'b
val getNthInt : int -> (string, string list) H.t -> string -> int
val getNthBool : int -> (string, string list) H.t -> string -> bool
val getBool : (string, string list) H.t -> string -> bool
val getInt : (string, string list) H.t -> string -> int
val getSizeof : (string, string list) H.t -> string -> int
val getAlignof : (string, string list) H.t -> string -> int
val respace : string -> string
val modelParse : string -> Machdep.mach
